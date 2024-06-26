import toml
import os
package_dir = os.path.dirname(__file__)

def get_status(args):
    try:
        with open(os.path.join(package_dir, 'status.toml'), 'r') as f:
            status = toml.load(f)
    except FileNotFoundError:
        print("Not connected")
        return
    connection = status['connection']
    server = status['server']
    wireguard = status['wireguard']
    print(f"Connected to {server['region']} ({server['cn']}) via WireGuard")
    print(f"Public IP address: {connection['pub_ip']}")
    if args.verbose:
        print(f"WireGuard IP address: {wireguard['ip']}")
        print(f"Server WireGuard IP: {wireguard['server_ip']}")
        print(f"Using DNS servers: {', '.join(connection['dns_servers'])}")
        print(f"Server endpoint: {server['ip']}:{server['port']}")
    if 'port_forward' in status:
        port_forward = status['port_forward']
        print(f"Forwarded port: {port_forward['port']}")
        if args.verbose:
            print(f"Port expires at: {port_forward['expires_at']}")
            print(f"Port last renewed at: {port_forward['last_renewed']}")
    if connection['disable_ipv6']:
        print("IPv6 disabled")
    else:
        print("IPv6 not disabled")
