import subprocess
import toml
import os
from .connect import connect, disconnect
package_dir = os.path.dirname(__file__)

def enable(args):
    """
    Create a persistent PIA WireGuard connection to the specified region
    by enabling a systemd service.
    """
    # first connect, then enable
    connect(args)

    subprocess.run(["sudo", "systemctl", "enable", "pia-vpn"])

def disable(args):
    """
    Disable the PIA systemd service and remove associated files.
    """
    # first disconnect, then disable
    disconnect(args)

    try:
        with open(os.path.join(package_dir, 'status.toml'), 'r') as f:
            status = toml.load(f)
    except FileNotFoundError:
        pass
    else:
        if 'port_forward' in status:
            subprocess.run(["sudo", "systemctl", "disable", "pia-pf-renew.timer"])
            subprocess.run(["sudo", "rm", "/etc/systemd/system/pia-pf-renew.timer"])
            subprocess.run(["sudo", "rm", "/etc/systemd/system/pia-pf-renew.service"])
    subprocess.run(["sudo", "systemctl", "disable", "pia-vpn"])
    subprocess.run(["sudo", "rm", "/etc/systemd/system/pia-vpn.service"])
    subprocess.run(["sudo", "rm", "/etc/wireguard/pia.conf"])
