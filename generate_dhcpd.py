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
import ipaddress
import pprint

# Regex to validate a hostname
HOSTNAME_REGEX = '^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$'

# Function to write a list of dictionaries to an ISC DHCPd configuration file
def dump_to_dhcpd(dhcpd_conf, out_file):
    with open(out_file, 'w') as f:
        for host in dhcpd_conf:      
            # Generate DHCPd configuration
            if host['comments']:    
                f.write('# {}\n'.format(host['comments']))
            f.write('host {} {{\n  hardware ethernet {};\n  fixed-address {};\n}}\n\n'.format(host['hostname'], host['mac'], host['ipv4']))

# Function to retrieve and validate a DHCP configuration
def validate_dhcp_config(records, ip_network):
    # Get the IP network
    vlan_cidr_network = ipaddress.ip_network(ip_network)
    
    # Create set of IP and MAC addresses to avoid duplicates
    ip_set = set()
    mac_set = set()
    
    # List of dictionaries, containing a clean-up list of hosts of the VLAN
    clean_records = list()
    
    # For every host     
    for host in records:
        # Extract info from dictionary
        hostname = host['Hostname'].strip().lower()
        mac = host['Mac Address'].strip()
        ipv4 = host['IPv4 address'].strip()
        comments = host['Note/commenti'].strip()
        
        # If any of those is empty, skip without raising anything
        if not (hostname and mac and ipv4):
            continue
     
        # Validate and transform MAC address to UNIX extended format (XX:XX:XX:XX:XX:XX)
        try:
            mac = netaddr.EUI(mac)
        except netaddr.AddrFormatError:        
            warnings.warn('{} is not a well-formed MAC address; skipping it...'.format(mac))
            continue
        mac.dialect = netaddr.mac_unix_expanded
        if mac not in mac_set:
            mac_set.add(mac)
        else:
            raise Exception('Duplicated MAC addess')
        
        # Validate hostname
        if not re.search(HOSTNAME_REGEX, hostname):
            warnings.warn('{} is not a well-formed hostname; skipping it...'.format(hostname))
            continue
            
        # Validate IPv4 address
        try:
            ipv4 = ipaddress.ip_address(ipv4)    
        except ValueError:        
            warnings.warn('{} is not a well-formed IPv4 address; skipping it...'.format(ipv4))
            continue
        
        # Verify if IP address is within the LAN and/or is duplicate    
        if ipv4 not in vlan_cidr_network:
            raise Exception('IPv4 outside of CIDR range.')
        if ipv4 not in ip_set:
            ip_set.add(ipv4)
        else:
            raise Exception('Duplicated IPv4 addess.')
        
        # Save result to a dictionary
        clean_records.append({'hostname': hostname,
                           'mac': mac,
                           'ipv4': ipv4,
                           'comments': comments})
    return clean_records

# Direct run (for testing only)
if __name__ == '__main__':
    # Read JSON
    with open("vlan601.json", "r") as f:
         records = json.load(f)
            
    # Validate
    dhcpd_conf = validate_dhcp_config(records, '10.61.0.0/24')
       
    # If everything went smoothly, then create a DHCPd file
    dump_to_dhcpd(dhcpd_conf, 'vlan_601.conf')
    
