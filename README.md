# GSheets DHCP generator

This scripts can:
1. Retrieve a list of hostnames/MAC addresses/IP addresses from different Google Sheets files (one per VLAN).
2. Validate that list.
3. Generate automatically a leases configuration for an [ISC DHCPd](https://www.isc.org/dhcp/) server.

## Usage

This software is divided into two files:
- A module [vlan.py](vlan.py), defining a `Vlan` class. This class makes all the low-level operations (retrieve data from Google, validate data, build config).
  This module uses [gspread](https://pypi.org/project/gspread/) to retrieve data from Google Sheets.
- A command-line script [dhcp_config_generator.py](dhcp_config_generator.py) to automatically run those operations in a Linux-based environment.

The script can be used with the following options:
```bash
$ ./dhcp_config_generator.py -h
usage: dhcp_config_generator.py [-h] [-o DIR] [-c JSON_FILE] [-l LOG_FILE]

Generate a set of ISC DHCPd configuration files from Google Sheets files.

optional arguments:
  -h, --help            show this help message and exit
  -o DIR, --output-dir DIR
                        Output dir for DHCPd configuration files.
  -c JSON_FILE, --config-json JSON_FILE
                        JSON-formatted configuration file.
  -l LOG_FILE, --log-file LOG_FILE
                        Log file.
```

## Installation


## TODO
Integrate with VlanMan to automatically add the MAC addresses to the RADIUS server for MAC-authentication.
