from requests import Session
from requests.adapters import HTTPAdapter

class DNSBypassAdapter(HTTPAdapter):
    """
    A Transport Adapter designed for communicating with a server over HTTPS
    when there is no public DNS record referring to it by the name specified
    in the corresponding TLS certificate.

    For whatever reason, PIA has decided that this is how API access to thier
    location-specific exit node servers works. These servers don't have public
    DNS records, but do serve HTTPS with a certificate signed by PIA's CA that
    specifies a "common name" that can be retrieved using the API. So to connect
    to them, you have to specify a hostname in your HTTP headers that isn't
    actually resolved via normal DNS. In the official manual-connections repo,
    they do this with curl's --connect-to option, but requests is a bit averse
    to doing something like this.

    The code for this class is based mainly on a StackOverflow answer by user
    Sarah Messer (https://stackoverflow.com/a/26473516).
    """
    def __init__(self, common_name, host, *args, **kwargs):
        """
        Create a DNSBypassAdapter for a specific server.

        Parameters
        ----------
        common_name: The server's hostname, as specified in its TLS certificate.
        host: The server's IP address (or publicly-resolvable hostname).
        """
        self.common_name = common_name
        self.host = host
        super().__init__(*args, **kwargs)

    def get_connection(self, url, proxies=None):
        """
        Override the get_connection() method of the base HTTPSAdapter,
        replacing instances of `common_name` with `host`.
        """
        redirected_url = url.replace(self.common_name, self.host)
        return super().get_connection(redirected_url, proxies=proxies)

    def get_connection_with_tls_context(self, request, verify, proxies=None, cert=None):
        """
        Replaces get_connection() in requests >= 2.32.
        For now I'm leaving both in place.
        """
        request.url = request.url.replace(self.common_name, self.host)
        return super().get_connection_with_tls_context(request, verify, proxies=proxies, cert=cert)

    def init_poolmanager(self, connections, maxsize, **kwargs):
        """
        Override the init_poolmanager() method of the base HTTPSAdapter,
        setting `assert_hostname` to `common_name`.
        """
        kwargs['assert_hostname'] = self.common_name
        super().init_poolmanager(connections, maxsize, **kwargs)
