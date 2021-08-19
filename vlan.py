# Basic class to manipulate a single VLAN: retrieve config from Google Sheets,
# create/dump to JSON, generate and validate a DHCP configuration, generate
# and validate a FreeRADIUS configuration on a MySQL database.
#
# Copyright (c) 2021 Istituto Nazionale di Ricerca Metrologica <d.pilori@inrim.it>
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
import re
import netaddr
import ipaddress
import os.path
import mysql.connector

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
         self.vlan_cidr_network = ipaddress.ip_network(ip_network)
             
         # If given, set a comment
         if comment:
             self.comment = comment
         
         # Initialize the DHCP and RADIUS config and the sheet records to empty list    
         self.sheet_records = list()
         self.dhcp_config = list()
         self.radius_config = list()
         
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
            oss = host['Sistema operativo'].strip()
            responsible = host['Referente'].strip()
            room = host['Stanza'].strip()
            description = host['Descrizione'].strip()
            
            # If any of those is empty, skip without raising anything
            if not (hostname and mac and ipv4):
                continue
         
            # Validate and transform MAC address to UNIX extended format (XX:XX:XX:XX:XX:XX)
            mac = netaddr.EUI(mac)
            mac.dialect = netaddr.mac_unix_expanded
            if mac not in mac_set:
                mac_set.add(mac)
            else:
                raise Exception('DHCP config: Duplicated MAC addess')
            
            # Validate hostname
            if not re.search(_HOSTNAME_REGEX, hostname):
                raise Exception('DHCP config: {} is not a well-formed hostname.'.format(hostname))
                
            # Validate IPv4 address
            ipv4 = ipaddress.ip_address(ipv4)    
            
            # Verify if IP address is within the LAN and/or is duplicate    
            if ipv4 not in self.vlan_cidr_network:
                raise Exception('DHCP config: IPv4 outside of CIDR range.')
            if ipv4 not in ip_set:
                ip_set.add(ipv4)
            else:
                raise Exception('DHCP config: duplicated IPv4 addess:"{}".'.format(ipv4))
            
            # Save result to a dictionary
            self.dhcp_config.append({'hostname': hostname,
                               'mac': mac,
                               'ipv4': ipv4,
                               'comments': comments,
                               'oss': oss,
                               'responsible': responsible,
                               'room': room,
                               'description': description})

    def dump_to_dhcpd(self, out_dir=''):
        """ Dump configuration to a DHCPd configuration file """
        if not self.dhcp_config:
            raise Exception('No DHCP config. Please run generate_dhcp_config() to generate a config.')
            
        # Add output dir, if given
        if out_dir:
            out_file = os.path.join(out_dir, self.dhcpd_out_file)
        else:
            out_file = self.dhcpd_out_file
  
        with open(out_file, 'w') as f:
            for host in self.dhcp_config:      
                # Generate DHCPd configuration
                f.write('# {} [{}]\n# {}, {}\n'.format(host['responsible'], host['room'], host['oss'], host['description']))
                if host['comments']:    
                    f.write('# {}\n'.format(host['comments']))
                f.write('host {} {{\n  hardware ethernet {};\n  fixed-address {};\n}}\n\n'.format(host['hostname'], host['mac'],
                        host['ipv4']))                               

    def generate_radius_config(self, json_in=''):
        """ Validate MAC address and prepare a list of MAC addresses to put into a RADIUS config. """                           
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
        
        # Re-initialize the RADIUS config
        self.radius_config = list()

        for host in self.sheet_records:
            # Extract info from dictionary
            mac = host['Mac Address'].strip()
            ipv4 = host['IPv4 address'].strip()

            # If there's no MAC address, just continue
            if not mac:
                continue
            
            # Validate and store MAC address
            mac = netaddr.EUI(mac)
            if mac not in mac_set:
                mac_set.add(mac)
            else:
                raise Exception('RADIUS config: duplicated MAC addess')
            
            # Validate IPv4 address, if present
            if ipv4:
                ipv4 = ipaddress.ip_address(ipv4)    
            
                # Verify if IP address is within the LAN and/or is duplicate    
                if ipv4 not in self.vlan_cidr_network:
                    raise Exception('RADIUS config: IPv4 outside of CIDR range.')
                if ipv4 not in ip_set:
                    ip_set.add(ipv4)
                else:
                    raise Exception('RADIUS config: duplicated IPv4 addess:"{}".'.format(ipv4))

            # Save result to a dictionary
            self.radius_config.append({'mac': mac,
                               'ipv4': ipv4})   
    
    def dump_to_radius_mysql(self, user, password, host, database, print_function=print):
        """ Dump the valudated set of MAC addresses to the MySQL FreeRADIUS database. """                           
        if not self.radius_config:
            raise Exception('No RADIUS config. Please run generate_radius_config() to generate a valid config.')
    
        # Open connection and cursor
        cnx = mysql.connector.connect(user=user, password=password,
                                  host=host,
                                  database=database)
        cur = cnx.cursor()

        # Get list of Mac-IP for the current VLAN
        cur.execute(('SELECT radcheck.username, radreply.value '
	                 ' FROM radcheck '
                     ' LEFT JOIN radreply ON ( '
                     '    radcheck.username = radreply.username '
                     '    AND radreply.attribute = "Framed-IP-Address"'
                     ' ) '
                     ' WHERE radcheck.username IN( '
    	             '    SELECT radcheck.username '
		             '    FROM radcheck '
    	             '    INNER JOIN radreply ON radcheck.username = radreply.username '
    	             '    WHERE radreply.value = %s AND radreply.attribute = "Tunnel-Private-Group-ID" '
                     ')'), (self.vlan_id, ))
        
        # Generate a set of current MAC addresses and a dictionary with MAC -> IPv4 bindings (if any)
        current_macs = set()
        ip_bindings = dict()
        for (mac, ipv4) in cur:
            current_macs.add(netaddr.EUI(mac))
            # Verify if an IPv4 is given or not
            if ipv4:
                ip_bindings[netaddr.EUI(mac)] = ipaddress.ip_address(ipv4)
            else:
                ip_bindings[netaddr.EUI(mac)] = None

        # Now process every content in Google Sheets, adding/removing it from the database
        for host in self.radius_config:
            # Extract info
            mac, ipv4 = host['mac'], host['ipv4']

            # Format MAC address as wanted by Aruba switches
            mac_format = mac.format(dialect=netaddr.mac_bare).lower()

            # First of all, check if the Mac already exists
            if mac in current_macs:
                # Remove from the list
                current_macs.remove(mac)

                # Check if IP binding is correct; if so, continue
                if ip_bindings[mac] == ipv4:
                    continue
                else:
                    # Otherwise, fix IP binding
                    cur.execute(('DELETE FROM radreply WHERE username = %s AND attribute = "Framed-IP-Address"'),
                               (mac_format,))

                    if ipv4:
                        cur.execute(('INSERT INTO radreply '
                            '(username, attribute, op, value) '
                            'VALUES (%s, %s, %s, %s)'),
                            (mac_format, 'Framed-IP-Address', ':=', format(ipv4)))
                        print_function('Setting new IPv4 address of host "{}": {}...'.format(mac, ipv4))
            
            # Mac is not present in this VLAN: add a new record
            else:
                # Check if host is currently present on a different VLAN, and, if so, remove it
                cur.execute(('DELETE FROM radcheck WHERE username = %s'), (mac_format,))
                if cur.rowcount >= 1:
                    print_function('Host "{}" is already present on a different VLAN; removing it...'.format(mac))
                cur.execute(('DELETE FROM radreply WHERE username = %s'),
                    (mac_format, ))

                # Add host to the authentication database
                cur.execute(('INSERT INTO radcheck '
                    '(username, attribute, op, value) '
                    'VALUES (%s, %s, %s, %s)'),
                    (mac_format, 'Auth-Type', ':=', 'Accept'))

                # Set VLAN id
                cur.execute(('INSERT INTO radreply '
                    '(username, attribute, op, value) '
                    'VALUES (%s, %s, %s, %s)'),
                    (mac_format, 'Tunnel-Private-Group-ID', ':=', self.vlan_id))
                # If set, set IPv4
                if ipv4:
                    cur.execute(('INSERT INTO radreply '
                        '(username, attribute, op, value) '
                        'VALUES (%s, %s, %s, %s)'),
                        (mac_format, 'Framed-IP-Address', ':=', format(ipv4)))

                # Print what is done
                if cur.rowcount >= 1:
                    print_function('Adding host {} to VLAN {}...'.format(mac, self.vlan_id))

        # Now remove all old MAC addresses
        for mac in current_macs:
            mac_format = mac.format(dialect=netaddr.mac_bare).lower()
            cur.execute(('DELETE FROM radcheck WHERE username = %s'), (mac_format,))
            if cur.rowcount >= 1:
                print_function('Removing host {} from VLAN {}...'.format(mac, self.vlan_id))
            cur.execute(('DELETE FROM radreply WHERE username = %s'), (mac_format,))
    
        # Commit all changes
        cnx.commit()

        # Close all
        cur.close()
        cnx.close()
