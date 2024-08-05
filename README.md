# PIA Manual Connection Service

This is a tool I wrote for manually connecting Linux devices to Private Internet Access VPN servers, based on [pia-foss/manual-connections]().
It can be used to create a one-time connection to PIA, or to create a persistent connection, which will be started automatically at boot, via a [systemd](https://github.com/systemd/systemd) service file.
Currently only WireGuard connections are working.

This repository is a Python package that can be installed with `pip`.
In addition to Python-level requirements listed in `pyproject.toml`, which will be installed automatically by `pip`, there are a few system-level requirements.
The WireGuard functionality requires `wg-quick` and `systemd-resolved` to be installed at the system level.
In addition, the CLI commands assume they are running as a user with `sudo` privileges.
Commands that modify the network configuration do so by launching subprocesses with `sudo`, and so will prompt for a `sudo` password.
This also means that `sudo` must be installed for the package to work properly.

To use, first download and install the Python package:
```bash
git clone git@github.com/rossjjennings/pia-service
cd pia-service
pip install .
```
This will make the `pia-service` command available.

To list the available PIA regions, run `pia-service list-regions`.
You can see details of each region, including the IP addresses of available OpenVPN and WireGuard servers, by running `pia-service region <region>`.
To connect to a server in a specific region, run `pia-service connect <region>`. You will be prompted for a PIA username and password, and then for a `sudo` password. The `-f` option can be used to request a forwarded port.
To check the status of the connection, use `pia-service status`.
While the connection is active, the systemd unit `pia-vpn.service` will be running. If port forwarding, an additional timer unit, `pia-pf-renew.service`, will also be running.
To disconnect from the VPN, run `pia-service disconnect`. This will leave the unit files `pia-vpn.service`, `pia-pf-renew.timer`, and `pia-pf-renew.service`, as well as the WireGuard configuration file `/etc/wireguard/pia.conf`, in place.

Optionally, you can store PIA login credentials by running `pia-service login`, and remove them with `pia-service logout`.

To create a persistent connection, run `pia-service enable <region>`. As with `connect`, the `-f` option can be used to request a forwarded port.
A connection can be disabled using `pia-service disable`. In addition to disabling the service files, and unlike `disconnect`, this will remove all files installed by `pia-service` outside of its directory, including the systemd unit files and the WireGuard configuration file.
