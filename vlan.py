# Basic class to manipulate a single VLAN: retrieve config from Google Sheets,
# create/dump to JSON, generate and validate a DHCP configuration.
#
# Copyright (c) 2021 Dario Pilori - INRiM <d.pilori@inrim.it>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# SPDX-License-Identifier: MIT

import gspread
import json
import warnings
import re
import netaddr
import ipaddress

# Simple regex to validate a hostname
_HOSTNAME_REGEX = '^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$'

class Vlan:
    """ Basic class to define a single VLAN, loading all the settings. """
    def __init__(self, vlan_id, ip_network, sheet_name, dhcpd_out_file, comment=''):
         """ Constructor to set the main VLAN parameters. """
         # Set VLAN id
         try:
             self.vlan_id = int(vlan_id)
             assert self.vlan_id >= 1 and self.vlan_id <= 4094
         except Exception as exc:
             raise Exception("Invalid VLAN id.") from exc
             
         # Set IP network
         try:
             self.vlan_cidr_network = ipaddress.ip_network(ip_network)
         except:
             raise Exception("Invalid IPv4 CIDR network.")
             
         # If given, set a comment
         if comment:
             self.comment = comment
         
         # Initialize the DHCP config and the sheet records to empty list    
         self.sheet_records = list()
         self.dhcp_config = list()
         
         # Set other parameters
         self.sheet_name = sheet_name
         self.dhcpd_out_file = dhcpd_out_file
         
    def retrieve_data(self, json_out=''):
        """ Retrieve updated data from a Google Sheet file. """     
        gc = gspread.service_account()
        sh = gc.open(self.sheet_name)
        
        self.sheet_records = sh.sheet1.get_all_records()
        self.dhcp_config = list()
        
        # If optional argument is given, dump to JSON
        if json_out:
            with open(json_out, 'w') as f:
                json.dump(self.sheet_records, f, indent=4)

    def generate_dhcp_config(self, json_in=''):
        """ Validate data and generate a DHCP config. """
        # If given, retrieve file from JSON
        if json_in:
            with open(json_in, 'r') as f:
                self.sheet_records = json.load(f)
        
        # Verify if the data has been retrieved from Google
        if not self.sheet_records:
            raise Exception('No data from Google Sheets. Please retrieve it before with retrieve_data().')
        
        # Create set of IP and MAC addresses to avoid duplicates
        ip_set = set()
        mac_set = set()
        
        # Re-initialize the DHCP config
        self.dhcp_config = list()
        
        # For every host     
        for host in self.sheet_records:
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
            if not re.search(_HOSTNAME_REGEX, hostname):
                warnings.warn('{} is not a well-formed hostname; skipping it...'.format(hostname))
                continue
                
            # Validate IPv4 address
            try:
                ipv4 = ipaddress.ip_address(ipv4)    
            except ValueError:        
                warnings.warn('{} is not a well-formed IPv4 address; skipping it...'.format(ipv4))
                continue
            
            # Verify if IP address is within the LAN and/or is duplicate    
            if ipv4 not in self.vlan_cidr_network:
                raise Exception('IPv4 outside of CIDR range.')
            if ipv4 not in ip_set:
                ip_set.add(ipv4)
            else:
                raise Exception('Duplicated IPv4 addess:"{}".'.format(ipv4))
            
            # Save result to a dictionary
            self.dhcp_config.append({'hostname': hostname,
                               'mac': mac,
                               'ipv4': ipv4,
                               'comments': comments})

    def dump_to_dhcpd(self):
        """ Dump configuration to a DHCPd configuration file """
        if not self.dhcp_config:
            raise Exception('No DHCP config. Please run generate_dhcp_config() to generate a config.')
  
        with open(self.dhcpd_out_file, 'w') as f:
            for host in self.dhcp_config:      
                # Generate DHCPd configuration
                if host['comments']:    
                    f.write('# {}\n'.format(host['comments']))
                f.write('host {} {{\n  hardware ethernet {};\n  fixed-address {};\n}}\n\n'.format(host['hostname'], host['mac'],
                        host['ipv4']))                               
                               
    
