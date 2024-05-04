import requests
import toml
from getpass import getpass

def get_token(askpass=False):
    """
    Get an authentication token from the PIA API.

    Parameters
    ----------
    askpass: Whether to prompt for the username and password interactively.
             If `False`, they will be read from the file `credentials.toml`.
    """
    if askpass:
        username = input("PIA username: ")
        password = getpass("PIA password: ")
    else:
        credentials = toml.load('credentials.toml')
        username = credentials['username']
        password = credentials['password']
    response = requests.post(
        'https://www.privateinternetaccess.com/api/client/v2/token',
        data = {'username': username, 'password': password},
    )
    token = response.json()['token']
    return token

def test_get_token(args):
    token = get_token(args.askpass)
    print(token)

