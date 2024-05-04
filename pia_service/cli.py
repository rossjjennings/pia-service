from .server_info import list_regions, region_info
from .get_token import test_get_token

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
    args = parser.parse_args()
    args.func(args)
