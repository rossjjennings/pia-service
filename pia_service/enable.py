import subprocess
import toml
import os
import sys
from .auth import get_token
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

    try:
        token = get_token()
    except AuthFailure as exc:
        print("PIA authentication failed. Received response:")
        print(exc.response)
        print("Exiting.")
        return
    else:
        print("PIA authentication OK")

    try:
        config, status = configure(
            token,
            args.region,
            args.hostname,
            not args.no_disable_ipv6
        )
    except KeyAddFailure as exc:
        print("Failed to add key to server. Response was:", file=sys.stderr)
        print(f"{exc.reponse}", file=sys.stderr)
        print("Exiting.", file=sys.stderr)
        return
    else:
        print("Successfully added WireGuard key to server")

    subprocess.run(["sudo", "mkdir", "-p", "/etc/wireguard"])
    subprocess.run(
        ["sudo", "tee", "/etc/wireguard/pia.conf"],
        input=config.encode('utf-8'),
        stdout=subprocess.DEVNULL,
    )

    service_template = jinja_env.get_template("pia-vpn.service.jinja")
    service = service_template.render(
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

    old_umask = os.umask(0o177)
    with open(os.path.join(package_dir, 'status.toml'), 'w') as f: 
        toml.dump(status, f)
    os.umask(old_umask)

def disable(args):
    """
    Disable the PIA systemd service and remove associated files.
    """
    subprocess.run(["sudo", "systemctl", "disable", "--now", "pia-vpn"])
    subprocess.run(["sudo", "rm", "/etc/wireguard/pia.conf"])
    os.remove(os.path.join(package_dir, 'status.toml'))

