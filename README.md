# PIA Manual Connection Service

This is a tool I wrote for manually connecting Linux devices to Private Internet Access VPN servers, based on [pia-foss/manual-connections]().
The goal is to create a working [systemd](https://github.com/systemd/systemd) service file that can be used to automatically connect at boot, but that is still a work in progress.
Currently working is a command-line interface that allows connecting over WireGuard.

This repository is a Python package that can be installed with `pip`.
In addition to Python-level requirements listed in `pyproject.toml`, which will be installed automatically by `pip`, there are a few system-level requirements.
The WireGuard functionality requires `wg-quick` and `resolvconf` to be installed at the system level.
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
To connect to a server in a specific region, run `pia-service connect <region>`. You will be prompted for a PIA username and password, and then for a `sudo` password.
To disconnect from the VPN, run `pia-service disconnect`.

Optionally, you can store PIA login credentials by running `pia-service login`, and remove them with `pia-service logout`.
