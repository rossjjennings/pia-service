import requests
import subprocess
import toml
import random
import os
import sys
from jinja2 import Environment, PackageLoader
jinja_env = Environment(loader=PackageLoader("pia_service"))
package_dir = os.path.dirname(__file__)

from .server_info import get_regions
from .transport import DNSBypassAdapter
from .auth import get_token
from .port_forward import forward_port

def create_keypair():
    """
    Create a WireGuard private key and the corresponding public key.
    """
    result = subprocess.run(["wg", "genkey"], capture_output=True)
    key = result.stdout.strip()
    result = subprocess.run(["wg", "pubkey"], input=key, capture_output=True)
    pubkey = result.stdout.strip()
    return key.decode('ascii'), pubkey.decode('ascii')

def add_key(token, pubkey, server):
    """
    Request that a PIA WireGuard server add a public key.

    Parameters
    ----------
    token: PIA authentication token
    pubkey: WireGuard public key
    server: Dictionary representing WireGuard server
     - key 'cn': Server common name
     - key 'ip': Server IP address
    """
    cn = server['cn']
    ip = server['ip']
    session = requests.Session()
    session.mount(f'https://{cn}', DNSBypassAdapter(cn, ip))
    response = session.get(
        f'https://{cn}:1337/addKey',
        params={'pt': token, 'pubkey': pubkey},
        verify=os.path.join(package_dir, "ca.rsa.4096.crt"),
    )
    return response.json()

def get_server(region, hostname=None):
    """
    Select and retrieve information about a WireGuard server from a specified
    PIA region. If `hostname` is specified, choose the server with that name.
    Otherwise, choose randomly from the available servers in the region.

    Parameters
    ----------
    region: Name of a PIA region
    hostname: (Optional) Hostname of preferred server

    Returns
    -------
    region: Dictionary representing PIA region
    server: Dictionary representing WireGuard server
     - key 'cn': Server common name
     - key 'ip': Server IP address
    """
    regions = get_regions()
    region = regions[region]
    if hostname is None:
        server = random.choice(region['servers']['wg'])
    else:
        wg_servers = {server['cn']: server for server in region['servers']['wg']}
        server = wg_servers[hostname]
    return region, server

def configure(region, hostname=None, disable_ipv6=True):
    """
    Set up a PIA WireGuard connection by creating a WireGuard keypair,
    adding the public key to a specified PIA server, and filling in the
    template WireGuard configuration.

    Parameters
    ----------
    region: Name of a PIA region
    hostname: (Optional) Hostname of preferred server
    disable_ipv6: Whether IPv6 is to be disabled (used only for status)

    Returns
    -------
    config: WireGuard configuration file with server details filled in
    status: Dictionary representing connection status
    """
    region, server = get_server(region, hostname)
    key, pubkey = create_keypair()
    
    token = get_token()
    if token is None:
        # authentication failed, and we already printed the message
        return

    result = add_key(token, pubkey, server)
    if not 'status' in result or not result['status'] == 'OK':
        print("Failed to add key to server. Response was:", file=sys.stderr)
        print(f"{result}", file=sys.stderr)
        print("Exiting.", file=sys.stderr)
        return
    config_template = jinja_env.get_template('pia.conf.jinja')
    config = config_template.render(
        peer_ip=result['peer_ip'],
        key=key,
        dns_servers=' '.join(ip for ip in result['dns_servers']),
        server_pubkey=result['server_key'],
        endpoint=f"{server['ip']}:{result['server_port']}",
    )

    status = {
        'connection': {
            'pub_ip': result['server_ip'],
            'dns_servers': result['dns_servers'],
            'disable_ipv6': disable_ipv6,
        },
        'wireguard': {
            'ip': result['peer_ip'],
            'server_ip': result['server_vip'],
            'key': key,
            'pubkey': pubkey,
            'server_pubkey': result['server_key'],
        },
        'server': {
            'region': region,
            'hostname': server['cn'],
            'ip': server['ip'],
            'port': result['server_port'],
            'allows_port_forwarding': region['port_forward'],
        },
    }

    return config, status

def connect(args):
    """
    Connect to a PIA WireGuard server in the specified region.
    """
    # abort if already connected
    if subprocess.run(["ip", "link", "show", "pia"], capture_output=True).returncode == 0:
        print('Device "pia" already exists, aborting.', file=sys.stderr)
        return

    result = configure(args.region, args.hostname, not args.no_disable_ipv6)
    config, status = result
    if config is None:
        # The above failed for some reason
        return

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

    if args.forward_port:
        status = forward_port(status, token)

    old_umask = os.umask(0o177)
    with open(os.path.join(package_dir, 'status.toml'), 'w') as f: 
        toml.dump(status, f)
    os.umask(old_umask)

def disconnect(args):
    """
    Disconnect from PIA.
    """
    subprocess.run(["sudo", "wg-quick", "down", "pia"])
    subprocess.run(["sudo", "rm", "/etc/wireguard/pia.conf"])
    subprocess.run(["sudo", "sysctl", "-w", "net.ipv6.conf.all.disable_ipv6=0"])
    subprocess.run(["sudo", "sysctl", "-w", "net.ipv6.conf.default.disable_ipv6=0"])
    os.remove(os.path.join(package_dir, 'status.toml'))

