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

class PortRequestTimeout(Exception):
    def __init__(self, uri):
        super().__init__(f"Request to {uri} timed out")
        self.uri = uri

def request_port(server, token):
    """
    Request a new port from the specified server.

    Parameters
    ----------
    server: Server from which to request a port
    token: A valid PIA authentication token

    Returns
    -------
    payload, signature: Payload and signature received from PIA
    """
    cn = server['cn']
    ip = server['ip']
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
        raise PortRequestTimeout(uri=f"https://{cn}:19999/getSignature")
    response_json = response.json()
    payload = response_json['payload']
    signature = response_json['signature']
    return payload, signature

def bind_port(server, payload, signature):
    """
    Bind a port for which we have already received a payload and signature.
    Requires an open connection to a server that allows port forwarding.

    Parameters
    ----------
    server: Server on which to bind the port
    payload, signature: Payload and signature received from PIA
    """
    cn = server['cn']
    ip = server['ip']
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

def forward_port(status, authority, wait=5):
    """
    Request that the server forward a port to the local host.
    Requires an open connection to a server that allows port forwarding.

    Parameters
    ----------
    status: Dictionary describing the connection status
     - key 'server': Server we are currently connected to
    authority: Credentials necessary to request and/or bind a port.
     * Alternative 1: Request a new port
       - key 'token': A valid PIA authentication token
     * Alternative 2: Use a previously received port
       - key 'payload': Payload containing port number and expiration date
       - key 'signature': Signature previously provided by PIA
    wait: Wait this many seconds before requesting the port
    """
    server = status['server']
    # Check that we are connected to a server that allows port forwarding
    if not server['allows_port_forwarding']:
        print(f"Current region ({status['server']['region']})"
                " does not allow port forwarding.", file=sys.stderr)
        print("Ignoring port forwarding request.", file=sys.stderr)
        return status

    if wait:
        print("Requesting forwarded port in ", end="", flush=True)
        for i in range(wait, 0, -1):
            print(f"{i}... ", end="", flush=True)
            time.sleep(1)
        print()

    if 'token' in authority:
        new_port = True
        token = authority['token']
        try:
            payload, signature = request_port(server, token)
        except PortRequestTimeout as exc:
            print(f"Request to {exc.uri} timed out", file=sys.stderr)
            print("Abandoning port forwarding request.", file=sys.stderr)
            return status
    elif 'payload' in authority and 'signature' in authority:
        new_port = False
        payload = authority['payload']
        signature = authority['signature']

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

    if new_port:
        old_umask = os.umask(0o177)
        with open(os.path.join(package_dir, "port_authority.toml"), "r") as f:
            authorities = toml.load(f)
        authorities['authority'].append(authority)
        with open(os.path.join(package_dir, "port_authority.toml"), "w") as f:
            toml.dump(authorities, f)
        os.umask(old_umask)

    bind_port(server, payload, signature)

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
    server = status['server']
    payload = status['port_forward']['payload']
    signature = status['port_forward']['signature']

    print(f"Attempting to re-bind to port {status['port_forward']['port']}")
    bind_port(server, payload, signature)
