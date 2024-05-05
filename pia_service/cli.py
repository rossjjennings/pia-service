from .server_info import list_regions, region_info
from .get_token import test_get_token
from .connect import connect, disconnect

def main():
    import argparse

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    parser_list_regions = subparsers.add_parser('list-regions',
        help="List available regions")
    parser_list_regions.set_defaults(func=list_regions)
    parser_region = subparsers.add_parser('region',
        help="List servers in a specified region")
    parser_region.set_defaults(func=region_info)
    parser_region.add_argument('region', type=str, help="Region to use")
    parser_token = subparsers.add_parser('token',
        help="Obtain an authentication token")
    parser_token.set_defaults(func=test_get_token)
    parser_token.add_argument('-a', '--askpass', action='store_true',
        help="Prompt for username and password")
    parser_connect = subparsers.add_parser('connect',
        help="Connect to a PIA VPN server in the specified region")
    parser_connect.set_defaults(func=connect)
    parser_connect.add_argument('-a', '--askpass', action='store_true',
        help="Prompt for username and password")
    parser_connect.add_argument('-t', '--allow-tailscale', action='store_true',
        help="Don't route Tailscale IP addresses (100.64.0.0/10) via PIA")
    parser_connect.add_argument('-6', '--no-disable-ipv6', action='store_true',
        help="Don't disable IPv6 while the PIA connection is active")
    parser_connect.add_argument('region', type=str, help="Specified region")
    parser_disconnect = subparsers.add_parser('disconnect',
        help="Disconnect from PIA")
    parser_disconnect.set_defaults(func=disconnect)
    args = parser.parse_args()
    args.func(args)
