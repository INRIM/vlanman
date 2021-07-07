#!/usr/bin/env python3
# Stupid test to synchronize the Mac addresses with the RADIUS' MySQL database.
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

import mysql.connector
import netaddr
import json

# Open connection and cursor
with open('mysql_settings.json', 'r') as f:
    mysql_settings = json.load(f)
cnx = mysql.connector.connect(**mysql_settings)
cur = cnx.cursor()

# Import data and VLAN_ID from Google Sheets using JSON (for testing)
vlan_id = 700
debug = True
with open('test_vlan700.json', 'r') as f:
    sheet_records = json.load(f)

# Get all current Mac Addresses of this VLAN from the database into a set
cur.execute('SELECT radcheck.username FROM radcheck '
            'INNER JOIN radreply ON radcheck.username=radreply.username '
            'WHERE radreply.value="{}" '
            'AND radreply.attribute="Tunnel-Private-Group-ID"'.format(vlan_id))
mac_addresses = set()
for (mac, ) in cur:
    mac_addresses.add(netaddr.EUI(mac))

# Now process every content in Google Sheets, adding/removing it from the database
for host in sheet_records:
    # Get Mac address
    mac = netaddr.EUI(host['Mac Address'])

    # If it exists in this VLAN, continue
    if mac in mac_addresses:
        mac_addresses.remove(mac)
        continue
    
    # Format MAC address as wanted by Aruba switches
    mac_format = mac.format(dialect=netaddr.mac_bare).lower()
   
    # Check if host is currently present on a different VLAN, and, if so, remove it
    cur.execute(('DELETE FROM radcheck WHERE username = %s'), (mac_format,))
    if cur.rowcount >= 0:
        print('Host {} is already present on a different VLAN; removing it...'.format(mac))
    cur.execute(('DELETE FROM radreply WHERE username = %s AND attribute = %s'),
                (mac_format, 'Tunnel-Private-Group-ID'))


    # If it does not exist, then add it to the authentication database
    cur.execute(('INSERT INTO radcheck '
                '(username, attribute, op, value) '
                'VALUES (%s, %s, %s, %s)'),
                (mac_format, 'Cleartext-Password', ':=', mac_format))

    # Remove any previous VLAN, and add the VLAN to the authorization database
    cur.execute(('INSERT INTO radreply '
                '(username, attribute, op, value) '
                'VALUES (%s, %s, %s, %s)'),
                (mac_format, 'Tunnel-Private-Group-ID', ':=', vlan_id))

    if cur.rowcount >= 0:
        print('Adding host {} to VLAN {}...'.format(mac, vlan_id))

# Now remove all old MAC addresses
for mac in mac_addresses:
    mac_format = mac.format(dialect=netaddr.mac_bare).lower()
    cur.execute(('DELETE FROM radcheck WHERE username = %s'), (mac_format,))
    cur.execute(('DELETE FROM radreply WHERE username = %s'), (mac_format,))
    print('Removing host {} from VLAN {}...'.format(mac, vlan_id))
    
# Commit these changes
cnx.commit()

# Close all
cur.close()
cnx.close()