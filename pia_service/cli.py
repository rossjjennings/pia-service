from pia_service.server_info import list_regions, region_info
from pia_service.auth import login, logout
from pia_service.connect import connect, disconnect
from pia_service.status import get_status
from pia_service.port_forward import forward_port, renew_port
from pia_service.enable import enable, disable

def main():
    import argparse

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(metavar="command")
    parser_list_regions = subparsers.add_parser('list-regions',
        help="List available regions")
    parser_list_regions.set_defaults(func=list_regions)
    parser_list_regions.add_argument('-g', '--no-geo', action='store_true',
        help="Show only non-geolocated regions")
    parser_list_regions.add_argument('-p', '--port-forward', action='store_true',
        help="Show only regions with port forwarding enabled")
    parser_region = subparsers.add_parser('region',
        help="List servers in a specified region")
    parser_region.set_defaults(func=region_info)
    parser_region.add_argument('region', type=str, help="Region to use")
    parser_connect = subparsers.add_parser('connect',
        help="Connect to a PIA VPN server in the specified region")
    parser_connect.set_defaults(func=connect)
    parser_connect.add_argument('-f', '--forward-port', action='store_true',
        help="Request a forwarded port from the server")
    parser_connect.add_argument('-F', '--request-new-port', action='store_true',
        help="Forward a port, ignoring previous ports and requesting a new one")
    parser_connect.add_argument('-6', '--no-disable-ipv6', action='store_true',
        help="Don't disable IPv6 while the PIA connection is active")
    parser_connect.add_argument('region', type=str, help="Specified region")
    parser_connect.add_argument('hostname', nargs='?', default=None,
        help="Hostname of specific server to connect to")
    parser_status = subparsers.add_parser('status',
        help="Check status of PIA connection")
    parser_status.set_defaults(func=get_status)
    parser_status.add_argument('-v', '--verbose', action='store_true',
        help="Print additional status information")
    parser_disconnect = subparsers.add_parser('disconnect',
        help="Disconnect from PIA")
    parser_disconnect.set_defaults(func=disconnect)
    parser_enable = subparsers.add_parser('enable',
        help="Create a persistent connection to a PIA VPN server")
    parser_enable.set_defaults(func=enable)
    parser_enable.add_argument('-f', '--forward-port', action='store_true',
        help="Forward a port, using previously forwarded port if possible")
    parser_enable.add_argument('-F', '--request-new-port', action='store_true',
        help="Forward a port, ignoring previous ports and requesting a new one")
    parser_enable.add_argument('-6', '--no-disable-ipv6', action='store_true',
        help="Don't disable IPv6 while the PIA connection is active")
    parser_enable.add_argument('region', type=str, help="Specified region")
    parser_enable.add_argument('hostname', nargs='?', default=None,
        help="Hostname of specific server to connect to")
    parser_disable = subparsers.add_parser('disable',
        help="Disable a connection and remove associated files")
    parser_disable.set_defaults(func=disable)
    parser_login = subparsers.add_parser('login',
        help="Store PIA username and password for future use")
    parser_login.set_defaults(func=login)
    parser_login = subparsers.add_parser('logout',
        help="Remove stored PIA username and password")
    parser_login.set_defaults(func=logout)
    parser_renew_port = subparsers.add_parser('renew-port',
        help="Renew the current port forward binding"
    )
    parser_renew_port.set_defaults(func=renew_port)
    args = parser.parse_args()
    args.func(args)

if __name__ == '__main__':
    main()
