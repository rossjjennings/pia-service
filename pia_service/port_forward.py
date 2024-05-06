import requests
import toml
import json
import os
import sys
import time
import base64

from .auth import get_token
from .transport import DNSBypassAdapter
package_dir = os.path.dirname(__file__)

def forward_port(status, token):
    """
    Request that the server forward a port to the local host.
    Requires an open connection to a server that allows port forwarding.

    Parameters
    ----------
    server: The server we are in the process of connecting to
    token: A valid PIA authentication token
    """
    # Check that we are connected to a server that allows port forwarding
    if not status['server']['allows_port_forwarding']:
        print(f"Current region ({status['server']['region']})"
                " does not allow port forwarding.", file=sys.stderr)
        print("Ignoring port forwarding request.", file=sys.stderr)
        return status
    else:
        print("Requesting forwarded port in ", end="", flush=True)
        for i in range(5, 0, -1):
            print(f"{i}... ", end="", flush=True)
            time.sleep(1)
        print()

    cn = status['server']['hostname']
    ip = status['server']['ip']
    session = requests.Session()
    session.mount(f'https://{cn}', DNSBypassAdapter(cn, ip))
    try:
        response = session.get(
            f'https://{cn}:19999/getSignature',
            params={'token': token},
            verify=os.path.join(package_dir, "ca.rsa.4096.crt"),
            timeout=5,
        )
    except requests.exceptions.Timeout:
        print(f"Request to https://{cn}:19999/getSignature timed out", file=sys.stderr)
        print("Abandoning port forwarding request.", file=sys.stderr)
        return status
    response_json = response.json()

    payload = response_json['payload']
    signature = response_json['signature']
    payload_json = json.loads(base64.b64decode(payload).decode('utf-8'))
    port = payload_json['port']
    expires_at = payload_json['expires_at']

    print(f"Received payload and signature for port {port}")
    print(f"Port expires at {expires_at}")

    authority = {
        'port': port,
        'expires_at': expires_at,
        'payload': payload,
        'signature': signature,
    }
    status['port_forward'] = authority
    old_umask = os.umask(0o177)
    with open(os.path.join(package_dir, "port_authority.toml"), "a+") as f:
        f.read() # now we're at the end of the file
        toml.dump({'authority': [authority]}, f)
    os.umask(old_umask)

    bind_port(cn, ip, payload, signature)

    return status

def renew_port(args):
    """
    Re-bind a port that is currently being forwarded, so that the server
    doesn't forget the mapping. Should be called every 15 minutes to keep
    a port open indefinitely.
    """
    try:
        with open(os.path.join(package_dir, 'status.toml'), 'r') as f:
            status = toml.load(f)
    except FileNotFoundError:
        print("Not connected", file=sys.stderr)
        return
    if 'port_forward' not in status:
        print("Port forwarding not active", file=sys.stderr)
        return
    cn = status['server']['hostname']
    ip = status['server']['ip']
    payload = status['port_forward']['payload']
    signature = status['port_forward']['signature']
    bind_port(cn, ip, payload, signature)

def bind_port(cn, ip, payload, signature):
    """
    Bind a port for which we have already received a payload and signature.
    Requires an open connection to a server that allows port forwarding.
    """
    session = requests.Session()
    session.mount(f'https://{cn}', DNSBypassAdapter(cn, ip))
    try:
        response = session.get(
            f'https://{cn}:19999/bindPort',
            params={'payload': payload, 'signature': signature},
            verify=os.path.join(package_dir, "ca.rsa.4096.crt"),
            timeout=5,
        )
    except requests.exceptions.Timeout:
        print(f"Request to https://{cn}:19999/bindPort timed out", file=sys.stderr)
        print("Abandoning attempt to bind port.", file=sys.stderr)
        return
    response_json = response.json()
    if 'status' not in response_json or response_json['status'] != 'OK':
        print("Failed to bind port. Response was:", file=sys.stderr)
        print(f"{response_json}", file=sys.stderr)
        print("Exiting.", file=sys.stderr)
        return
    else:
        payload_json = json.loads(base64.b64decode(payload).decode('utf-8'))
        port = payload_json['port']
        print(f"Successfully bound to port {port}")
        if 'message' in response_json:
            print(f"Server responds: {response_json['message']}")
