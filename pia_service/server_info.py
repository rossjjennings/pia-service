import requests
import json

def get_regions(as_dict=True):
    response = requests.get('https://serverlist.piaservers.net/vpninfo/servers/v6')
    info = json.loads(response.content.decode('utf-8').split('\n')[0])
    if as_dict:
        return {region['id']: region for region in info['regions']}
    else:
        return info['regions']

def list_regions(args):
    regions = get_regions(as_dict=False)
    if args.no_geo:
        regions = [region for region in regions if not region['geo']]
    if args.port_forward:
        regions = [region for region in regions if region['port_forward']]
    print('Available regions:')
    for region in sorted(regions, key=lambda region: region['name']):
        print(f" - {region['name']} ({region['id']})")

def region_info(args):
    regions = get_regions()
    region = regions[args.region]
    servers = region['servers']
    print(f"Name: {region['name']}")
    print(f"Country: {region['country']}")
    print(f"Geolocated: {region['geo']}")
    print(f"Offline: {region['offline']}")
    print(f"Port forwarding: {region['port_forward']}")
    print('WireGuard servers:')
    for server in servers['wg']:
        print(f" - {server['cn']} @ {server['ip']}")

