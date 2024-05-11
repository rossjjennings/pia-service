import requests
import toml
from getpass import getpass
import os.path
package_dir = os.path.dirname(__file__)

class AuthFailure(Exception):
    def __init__(self, response):
        super().__init__(response)
        self.response = response

def get_credentials():
    """
    Get the user's PIA username and password, either from disk by
    interactively requesting them from the user.
    """
    try:
        credentials = toml.load(os.path.join(package_dir, 'credentials.toml'))
    except FileNotFoundError:
        username = input("PIA username: ")
        password = getpass("PIA password: ")
    else:
        username = credentials['username']
        password = credentials['password']
    return username, password

def get_token(username=None, password=None):
    """
    Get an authentication token from the PIA API.

    Parameters
    ----------
    askpass: Whether to prompt for the username and password interactively.
             If `False`, they will be read from the file `credentials.toml`.
    """
    if username is None or password is None:
        username, password = get_credentials()
    response = requests.post(
        'https://www.privateinternetaccess.com/api/client/v2/token',
        data = {'username': username, 'password': password},
    )
    try:
        response_json = response.json()
    except requests.JSONDecodeError as e:
        response_content = response.content.decode('utf-8').strip()
        raise AuthFailure(response=response_content) from None
    token = response_json['token']
    return token

def login(args):
    """
    Request and store the user's PIA username and password, taking care
    to deny read/write permissions to anyone but the owner.

    This does store the credentials on disk in an unencrypted format, which
    is not ideal security-wise. However, in this context it's probably an
    acceptable risk for most people, as long as the host machine itself is
    relatively secure. And we want the credentials to be accessible without
    user interaction (e.g., so the service can connect automatically at boot),
    so there are few other options.
    """
    try:
        credentials = toml.load(os.path.join('credentials.toml'))
    except FileNotFoundError:
        pass
    else:
        print(f"You are already logged in (username: {credentials['username']}).")
        print("To log out, run 'pia-service logout'.")
        return
    username = input("PIA username: ")
    password = getpass("PIA password: ")

    # Make sure the username and password are valid
    token = get_token(username, password)
    if token is None:
        # authentication failed, and we already printed the message
        return

    contents = f'username = "{username}"\npassword = "{password}"\n'
    old_umask = os.umask(0o177)
    credentials_path = os.path.join(package_dir, 'credentials.toml')
    with open(credentials_path, 'w') as f:
        f.write(contents)
    os.umask(old_umask)
    print(f"Recorded credentials at {credentials_path}")

def logout(args):
    """
    Remove the stored username and password, if there is one.
    """
    credentials_path = os.path.join(package_dir, 'credentials.toml')
    try:
        os.remove(credentials_path)
    except FileNotFoundError:
        pass
    else:
        print(f"Removed credential file {credentials_path}")

def test_get_token(args):
    token = get_token()
    print(token)

