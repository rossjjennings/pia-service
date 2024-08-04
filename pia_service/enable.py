import subprocess
import toml
import os
import sys
import site
from .auth import get_token, AuthFailure
from .connect import configure, KeyAddFailure
from .port_forward import forward_port
from jinja2 import Environment, PackageLoader
jinja_env = Environment(loader=PackageLoader("pia_service"), trim_blocks=True)
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

    service_template = jinja_env.get_template("pia-vpn.service.jinja")
    cli_cmd = sys.executable + " " + os.path.join(package_dir, "cli.py")
    service = service_template.render(
        site_packages=site.getusersitepackages(),
        pia_service=cli_cmd,
        forward_port=args.forward_port,
        python_interpreter=sys.executable,
        package_dir=package_dir,
        args=f"{args.region}",
    )
    subprocess.run(
        ["sudo", "tee", "/etc/systemd/system/pia-vpn.service"],
        input=service.encode('utf-8'),
        stdout=subprocess.DEVNULL,
    )
    subprocess.run(["sudo", "systemctl", "enable", "--now", "pia-vpn"])

    if args.forward_port:
        # TODO: Persist this too
        status = forward_port(status, token)

def disable(args):
    """
    Disable the PIA systemd service and remove associated files.
    """
    subprocess.run(["sudo", "systemctl", "disable", "--now", "pia-vpn"])
    subprocess.run(["sudo", "rm", "/etc/systemd/system/pia-vpn.service"])
    subprocess.run(["sudo", "rm", "/etc/wireguard/pia.conf"])

