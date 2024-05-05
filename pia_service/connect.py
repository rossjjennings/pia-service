import requests
import subprocess
import toml
import random
import os
import sys
from jinja2 import Environment, PackageLoader
jinja_env = Environment(loader=PackageLoader("pia_service"))
package_dir = os.path.dirname(__file__)

from pia_service.server_info import get_regions
from pia_service.transport import DNSBypassAdapter
from pia_service.auth import get_token

def create_keypair():
    """
    Create a WireGuard private key and the corresponding public key.
    """
    result = subprocess.run(["wg", "genkey"], capture_output=True)
    key = result.stdout.strip()
    result = subprocess.run(["wg", "pubkey"], input=key, capture_output=True)
    pubkey = result.stdout.strip()
    return key.decode('ascii'), pubkey.decode('ascii')

def add_key(token, pubkey, cn, ip):
    """
    Request that a PIA WireGuard server add a public key.

    Parameters
    ----------
    token: PIA authentication token
    pubkey: WireGuard public key
    cn: Common name of WireGuard server
    ip: IP address of WireGuard server
    """
    session = requests.Session()
    session.mount(f'https://{cn}', DNSBypassAdapter(cn, ip))
    response = session.get(
        f'https://{cn}:1337/addKey',
        params={'pt': token, 'pubkey': pubkey},
        verify=os.path.join(package_dir, "ca.rsa.4096.crt"),
    )
    return response.json()

def connect(args):
    """
    Connect to a PIA WireGuard server in the specified region.
    """
    regions = get_regions()
    region = regions[args.region]
    if args.hostname is None:
        wg_server = random.choice(region['servers']['wg'])
    else:
        wg_servers = {server['cn']: server for server in region['servers']['wg']}
        wg_server = wg_servers[args.hostname]

    key, pubkey = create_keypair()

    token = get_token()
    if token is None:
        # authentication failed, and we already printed the message
        return

    result = add_key(token, pubkey, wg_server['cn'], wg_server['ip'])
    if not 'status' in result or not result['status'] == 'OK':
        print("Failed to add key to server. Response was:", file=sys.stderr)
        print(f"{result}", file=sys.stderr)
        print("Exiting.", file=sys.stderr)
        return
    if args.allow_tailscale:
        allowed_ips=('0.0.0.0/2, 64.0.0.0/3, 96.0.0.0/6, 100.0.0.0/10, '
                     '100.128.0.0/9, 101.0.0.0/8, 102.0.0.0/7, 104.0.0.0/5, '
                     '112.0.0.0/4, 128.0.0.0/1')
    else:
        allowed_ips='0.0.0.0/0'

    config_template = jinja_env.get_template('pia.conf.jinja')
    config = config_template.render(
        peer_ip=result['peer_ip'],
        key=key,
        dns_servers=', '.join(ip for ip in result['dns_servers']),
        server_pubkey=result['server_key'],
        allowed_ips=allowed_ips,
        endpoint=f"{wg_server['ip']}:{result['server_port']}",
    )

    status = {
        'connection': {
            'pub_ip': result['server_ip'],
            'dns_servers': result['dns_servers'],
            'disable_ipv6': not args.no_disable_ipv6,
            'allow_tailscale': args.allow_tailscale,
        },
        'wireguard': {
            'ip': result['peer_ip'],
            'server_ip': result['server_vip'],
        },
        'server': {
            'region': args.region,
            'hostname': wg_server['cn'],
            'ip': wg_server['ip'],
            'port': result['server_port'],
        },
    }
    old_umask = os.umask(0o177)
    with open(os.path.join(package_dir, 'status.toml'), 'w') as f: 
        toml.dump(status, f)
    os.umask(old_umask)

    if not args.no_disable_ipv6:
        subprocess.run(["sudo", "sysctl", "-w", "net.ipv6.conf.all.disable_ipv6=1"])
        subprocess.run(["sudo", "sysctl", "-w", "net.ipv6.conf.default.disable_ipv6=1"])
    subprocess.run(["sudo", "mkdir", "-p", "/etc/wireguard"])
    subprocess.run(
        ["sudo", "tee", "/etc/wireguard/pia.conf"],
        input=config.encode('utf-8'),
        stdout=subprocess.DEVNULL,
    )
    subprocess.run(["sudo", "wg-quick", "up", "pia"])

def disconnect(args):
    """
    Disconnect from PIA.
    """
    subprocess.run(["sudo", "wg-quick", "down", "pia"])
    subprocess.run(["sudo", "rm", "/etc/wireguard/pia.conf"])
    subprocess.run(["sudo", "sysctl", "-w", "net.ipv6.conf.all.disable_ipv6=0"])
    subprocess.run(["sudo", "sysctl", "-w", "net.ipv6.conf.default.disable_ipv6=0"])
    os.remove(os.path.join(package_dir, 'status.toml'))

