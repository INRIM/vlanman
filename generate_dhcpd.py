#!/usr/bin/env python3
# generate_dhcpd.py
# Simple script to generate an ISC DHCPd leases
# configuration, starting from a JSON file
# extracted from a Google Sheets file.

# Copyright (c) 2021 Dario Pilori, INRiM <d.pilori@inrim.it>
# SPDX-License-Identifier: MIT

import json
import warnings
import re
import netaddr

hostname_regex = '^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$'
vlan_cidr_network = netaddr.IPNetwork('10.71.0.0/24')

with open("vlan701.json", "r") as f:
    records = json.load(f)
    
for host in records:
    # Extract info
    hostname = host['Hostname'].strip()
    mac = host['Mac Address'].strip()
    ipv4 = host['IPv4 address'].strip()
    comments = host['Note/commenti'].strip()
    
    # If any of those is empty, skip without raising anything
    if not (hostname and mac and ipv4):
        continue
 
    # Validate and transform MAC address to UNIX format (XX:XX:XX:XX:XX:XX)
    try:
        mac = netaddr.EUI(mac)
    except netaddr.AddrFormatError:        
        print('{} is not a well-formed MAC address; skipping.'.format(mac))
        continue
    mac.dialect = netaddr.mac_unix_expanded
    
    # Validate hostname
    if not re.search(hostname_regex, hostname):
        warnings.warn('{} is not a well-formed hostname; skipping.'.format(hostname))
        continue
        
    # Validate IPv4 address
    try:
        ipv4 = netaddr.IPAddress(ipv4)    
    except netaddr.AddrFormatError:        
        print('{} is not a well-formed IPv4 address; skipping.'.format(ipv4))
        continue
    if ipv4 not in vlan_cidr_network:
        print('{} is not part of the network; skipping.'.format(ipv4))
        continue
        
    # Generate DHCPd configuration
    if comments:    
        print('# {}'.format(comments))

    print('Host {} {{\n  hardware ethernet {};\n  fixed-address {};\n}}\n'.format(hostname, mac, ipv4))
    
