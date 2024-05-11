import subprocess
import toml
import os
import sys
from .connect import configure
from .port_forward import forward_port
package_dir = os.path.dirname(__file__)

def enable(args):
    """
    Create a persistent PIA WireGuard connection to the specified region
    by enabling a systemd service.
    """
    # abort if already connected
    if subprocess.run(["ip", "link", "show", "pia"], capture_output=True).returncode == 0:
        print('Device "pia" already exists, aborting.', file=sys.stderr)
        return

    result = configure(args.region, args.hostname, not args.no_disable_ipv6)
    config, status = result
    if config is None:
        # The above failed for some reason
        return

    subprocess.run(["sudo", "mkdir", "-p", "/etc/wireguard"])
    subprocess.run(
        ["sudo", "tee", "/etc/wireguard/pia.conf"],
        input=config.encode('utf-8'),
        stdout=subprocess.DEVNULL,
    )
    subprocess.run(["sudo", "systemctl", "enable", "--now", "wg-quick@pia"])

    if args.forward_port:
        # TODO: Persist this too
        status = forward_port(status, token)

    old_umask = os.umask(0o177)
    with open(os.path.join(package_dir, 'status.toml'), 'w') as f: 
        toml.dump(status, f)
    os.umask(old_umask)

def disable(args):
    """
    Disable the PIA systemd service and remove associated files.
    """
    subprocess.run(["sudo", "systemctl", "disable", "--now", "wg-quick@pia"])
    subprocess.run(["sudo", "rm", "/etc/wireguard/pia.conf"])
    os.remove(os.path.join(package_dir, 'status.toml'))

