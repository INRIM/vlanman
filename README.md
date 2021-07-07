# GSheets VLAN generator

This scripts can:
1. Retrieve a list of hostnames/MAC addresses/IP addresses from different Google Sheets files (one per VLAN).
2. Validate that list.
3. Generate automatically a leases configuration for an [ISC DHCPd](https://www.isc.org/dhcp/) server.
4. Synchronize a MySQL database of authorized Mac Addresses, to be read by [FreeRADIUS](https://freeradius.org/).

## Usage

This software is divided into two files:
- A module [vlan.py](vlan.py), defining a `Vlan` class. This class makes all the low-level operations (retrieve data from Google, validate data, build config).
  This module uses [gspread](https://pypi.org/project/gspread/) to retrieve data from Google Sheets.
- A command-line script [vlan_config_generator.py](vlan_config_generator.py) to automatically run those operations in a Linux-based environment.

The script can be used with the following options:
```bash
$ ./vlan_config_generator.py -h
usage: vlan_config_generator.py [-h] [-o DIR] [-c JSON_FILE] [-l LOG_FILE]

Generate a set of ISC DHCPd configuration files and synchronize FreeRADIUS from Google Sheets files

optional arguments:
  -h, --help            show this help message and exit
  -o DIR, --output-dir DIR
                        Output dir for DHCPd configuration files.
  -c JSON_FILE, --config-json JSON_FILE
                        JSON-formatted configuration file.
  -l LOG_FILE, --log-file LOG_FILE
                        Log file.
```

### Google Sheet format
The Google Sheet file *must* have the following structure:
- On each row there's a single host to be registered.
- The first row contains the labels of each column.
- At least, the following columns must be present: `Hostname`, `Mac Address`, `IPv4 address` and `Note/commenti`.
- Everything else is ignored.

Each row containing an hostname, a MAC address and an IPv4 address is evaluated. Others are discarded.
If any hostname, MAC Address or IPv4 address is not valid, the software triggers an error and it
skips **the entire VLAN**. This is meant to always have a consistent and fully-valid DHCPd configuration for every VLAN,
even if the configuration is slightly outdated.

## Installation with Docker
This software has been designed to be run periodically (e.g. with cron) using a [Docker](https://www.docker.com/) container.

1. Create a Google Service account with read access to the wanted Google Sheets file, and download the credentials into a JSON
   file called `service_account.json`. You can follow the steps from the Gspread documentation: https://gspread.readthedocs.io/en/latest/oauth2.html.
2. Install the latest version of Docker CE for your distribution: https://docs.docker.com/engine/install/.
3. Create a Docker [volume](https://docs.docker.com/storage/volumes/), which will contain:
   - The configuration file, with the list of VLAN and their associated Google Sheets file.
   - The output DHCPd configuration files.
```bash
docker volume create gsheets-vlan-gen   
```
4. Create a configuration JSON file, containing the list of the VLANs and their associated informations. This file will be called `list_vlans.json`. For example:
```json
[
    {
        "vlan_id": 999,
        "ip_network": "192.0.2.0/24",
        "sheet_name": "TEST_VLAN999",
        "dhcpd_out_file": "vlan_999.conf",
        "comment": "Test VLAN 999"    
    },
    [...]
]
```
5. Copy the configuration JSON file to the Docker volume created before. E.g.:
```bash
cp list_vlans.json /var/lib/docker/volumes/gsheets-vlan-gen/_data
```
6. Clone this repository and build a Docker image
```bash
docker build -t gsheets-vlan-gen .
```
7. Once created the image, you can *manually* build the new configurations with the following command:
```bash
docker run --rm -v gsheets-vlan-gen:/var/lib/dhcp-config-gen gsheets-vlan-gen
```
  The files and the logfile will be created inside the Docker volume, i.e. in `/var/lib/docker/volumes/gsheets-vlan-gen`.
8. The command written previously can be scripted, e.g. using crontab, to periodically generate new configuration.

### Periodic update with systemd timer
A good solution is the use of [systemd timers](https://wiki.archlinux.org/index.php/Systemd/Timers) to periodically
update the configuraiton files. In the `systemd` directory there are scripts to help doing so. To install them:
1. Copy `gsheets-vlan-gen.service` and `gsheets-vlan-gen.timer` to `/etc/systemd/system`.
2. Copy `gsheets-vlan-gen.sh` to `/usr/local/bin`.
3. Reload systemd:
```bash
systemctl daemon-reload
```
4. Enable systemd timer
```bash
systemctl --now enable gsheets-vlan-gen.timer
```
