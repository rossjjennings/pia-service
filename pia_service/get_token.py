import requests
import toml

def get_token(username, password):
    response = requests.post(
        'https://www.privateinternetaccess.com/api/client/v2/token',
        data = {'username': username, 'password': password},
    )
    token = response.json()['token']
    return token

def print_token(args):
    credentials = toml.load('credentials.toml')
    token = get_token(credentials['username'], credentials['password'])
    print(token)

