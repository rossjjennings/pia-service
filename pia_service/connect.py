import requests
import subprocess
import toml
import random
import os
import sys
import getpass
import sysconfig
from datetime import datetime
from jinja2 import Environment, PackageLoader
jinja_env = Environment(loader=PackageLoader("pia_service"), trim_blocks=True)
package_dir = os.path.dirname(__file__)

from .server_info import get_regions
from .transport import DNSBypassAdapter
from .auth import get_token, AuthFailure
from .port_forward import forward_port

class KeyAddFailure(Exception):
    def __init__(self, response):
        super().__init__(response)
        self.response = response

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
    response_json = response.json()
    if not 'status' in response_json or not response_json['status'] == 'OK':
        raise KeyAddFailure(response=response_json)
    return response_json

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

def configure(token, region, hostname=None, disable_ipv6=True):
    """
    Set up a PIA WireGuard connection by creating a WireGuard keypair,
    adding the public key to a specified PIA server, and filling in the
    template WireGuard configuration.

    Parameters
    ----------
    token: Valid PIA authentication token
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

    result = add_key(token, pubkey, server)
    config_template = jinja_env.get_template('pia.conf.jinja')
    config = config_template.render(
        peer_ip=result['peer_ip'],
        key=key,
        dns_servers=' '.join(ip for ip in result['dns_servers']),
        server_pubkey=result['server_key'],
        endpoint=f"{server['ip']}:{result['server_port']}",
        disable_ipv6=disable_ipv6,
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
            'region': region['name'],
            'cn': server['cn'],
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

    try:
        token = get_token()
    except AuthFailure as exc:
        print("PIA authentication failed. Received response:")
        print(exc.response)
        print("Exiting.")
        return
    else:
        print("PIA authentication OK")

    try:
        config, status = configure(
            token,
            args.region,
            args.hostname,
            not args.no_disable_ipv6
        )
    except KeyAddFailure as exc:
        print("Failed to add key to server. Response was:", file=sys.stderr)
        print(f"{exc.reponse}", file=sys.stderr)
        print("Exiting.", file=sys.stderr)
        return
    else:
        print("Successfully added WireGuard key to server")

    subprocess.run(["sudo", "mkdir", "-p", "/etc/wireguard"])
    subprocess.run(
        ["sudo", "tee", "/etc/wireguard/pia.conf"],
        input=config.encode('utf-8'),
        stdout=subprocess.DEVNULL,
    )

    service_template = jinja_env.get_template("pia-vpn.service.jinja")
    service = service_template.render(forward_port=args.forward_port)
    subprocess.run(
        ["sudo", "tee", "/etc/systemd/system/pia-vpn.service"],
        input=service.encode('utf-8'),
        stdout=subprocess.DEVNULL,
    )
    subprocess.run(["sudo", "systemctl", "start", "pia-vpn.service"])

    try:
        if args.forward_port or args.request_new_port:
            timer = jinja_env.get_template("pia-pf-renew.timer").render()
            timer_service = jinja_env.get_template("pia-pf-renew.service.jinja").render(
                user=getpass.getuser(),
                pia_service=os.path.join(sysconfig.get_path("scripts"), "pia-service"),
            )
            subprocess.run(
                ["sudo", "tee", "/etc/systemd/system/pia-pf-renew.timer"],
                input=timer.encode('utf-8'),
                stdout=subprocess.DEVNULL,
            )
            subprocess.run(
                ["sudo", "tee", "/etc/systemd/system/pia-pf-renew.service"],
                input=timer_service.encode('utf-8'),
                stdout=subprocess.DEVNULL,
            )
            subprocess.run(["sudo", "systemctl", "start", "pia-pf-renew.timer"])

            authorities = {}
            authority_file = os.path.join(package_dir, "port_authority.toml")
            if os.path.exists(authority_file):
                with open(authority_file, 'r') as f:
                    authorities = toml.load(f)['authority']
            if args.forward_port and authorities:
                # get most recent authority
                authority = max(authorities, key=lambda auth: auth['expires_at'])
                # check expiration
                # PIA provides expiration dates to ns precision, but `datetime`
                # doesn't know how to handle that, and the relevant clocks aren't
                # that accurate anyway, so truncate at the us level.
                expiration = datetime.strptime(
                    authority['expires_at'][:26], '%Y-%m-%dT%H:%M:%S.%f'
                )
                if datetime.utcnow() >= expiration:
                    print(f"Authority for port {authority['port']} is expired")
                    print("Requesting new forwarded port")
                    authority = {'token': token}
                else:
                    print(f"Attempting to bind existing port {authority['port']}")
            else:
                authority = {'token': token}
                print("Requesting new forwarded port")

            status = forward_port(status, authority)
    finally:
        # make sure to write the status file even if we hit an exception
        # during port forwarding somewhere
        old_umask = os.umask(0o177)
        with open(os.path.join(package_dir, 'status.toml'), 'w') as f:
            toml.dump(status, f)
        os.umask(old_umask)

def disconnect(args):
    """
    Disconnect from PIA.
    """
    try:
        with open(os.path.join(package_dir, 'status.toml'), 'r') as f:
            status = toml.load(f)
    except FileNotFoundError:
        pass
    else:
        if 'port_forward' in status:
            subprocess.run(["sudo", "systemctl", "stop", "pia-pf-renew.timer"])
    subprocess.run(["sudo", "systemctl", "stop", "pia-vpn.service"])
    os.remove(os.path.join(package_dir, 'status.toml'))

