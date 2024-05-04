import requests
import subprocess
import random
import sys
from jinja2 import Environment, PackageLoader
jinja_env = Environment(loader=PackageLoader("pia_service"))

from pia_service.server_info import get_regions
from pia_service.transport import DNSBypassAdapter
from pia_service.get_token import get_token

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
        verify="ca.rsa.4096.crt",
    )
    return response.json()

def connect(args):
    """
    Connect to a PIA WireGuard server in the specified region.
    """
    regions = get_regions()
    region = regions[args.region]
    wg_server = random.choice(region['servers']['wg'])

    key, pubkey = create_keypair()

    token = get_token(askpass=args.askpass)
    result = add_key(token, pubkey, wg_server['cn'], wg_server['ip'])
    if not 'status' in result or not result['status'] == 'OK':
        print("Failed to add key to server. Response was:", file=sys.stderr)
        print(f"{result}", file=sys.stderr)
        print("Exiting.", file=sys.stderr)
        return

    config_template = jinja_env.get_template('pia.conf.jinja')
    config = config_template.render(
        peer_ip=result['peer_ip'],
        key=key,
        dns_servers=', '.join(ip for ip in result['dns_servers']),
        server_pubkey=result['server_key'],
        allowed_ips='0.0.0.0/0',
        endpoint=f"{wg_server['ip']}:{result['server_port']}",
    )

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

