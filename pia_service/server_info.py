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
    print('OpenVPN TCP servers:')
    for server in servers['ovpntcp']:
        print(f" - {server['cn']} @ {server['ip']}")
    print('OpenVPN UDP servers:')
    for server in servers['ovpnudp']:
        print(f" - {server['cn']} @ {server['ip']}")
    print('WireGuard servers:')
    for server in servers['wg']:
        print(f" - {server['cn']} @ {server['ip']}")

