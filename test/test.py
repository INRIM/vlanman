# Test the Vlan class.
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

import sys
sys.path.append('../')

import unittest
from vlan import Vlan
import filecmp
import json
import mysql.connector
import netaddr

class TestVlan(unittest.TestCase):
    def compare_databases(self, mysql_settings, json_in):
        # Get all Mac Addresses of this VLAN from the database into a set
        cnx = mysql.connector.connect(**mysql_settings)
        cur = cnx.cursor()
        cur.execute('SELECT radcheck.username FROM radcheck '
            'INNER JOIN radreply ON radcheck.username=radreply.username '
            'WHERE radreply.value="{}" '
            'AND radreply.attribute="Tunnel-Private-Group-ID"'.format(601))
        mysql_mac_addresses = set()
        for (mac, ) in cur:
            mysql_mac_addresses.add(netaddr.EUI(mac))
        cur.close()
        cnx.close()

        # Load MAC addresses from JSON
        with open(json_in, 'r') as f:
            test_vlan_json = json.load(f)
        json_mac_addresses = set()
        for host in test_vlan_json:
            json_mac_addresses.add(netaddr.EUI(host['Mac Address']))

        return json_mac_addresses == mysql_mac_addresses


    def test_dhcp_validation(self):
        """ Import a test vlan JSON and verify that the output DHCP config is correct. """
        vlan_test = Vlan(601, '10.61.0.0/24', 'VLAN_TEST', 'test_vlan_unittest.conf')
        vlan_test.generate_dhcp_config(json_in='test_vlan.json')
        vlan_test.dump_to_dhcpd()
        self.assertTrue(filecmp.cmp('test_vlan_unittest.conf', 'test_vlan.conf'))
    
    def test_radius_sql(self):
        """ Import a test vlan JSON and verify that the MAC addresses are successfully added to DHCP. """
        vlan_test = Vlan(601, '10.61.0.0/24', 'VLAN_TEST', 'test_vlan_unittest.conf')
        vlan_test.generate_radius_config(json_in='test_vlan.json')
        with open('test_mysql_settings.json', 'r') as f:
                mysql_settings = json.load(f)
        vlan_test.dump_to_radius_mysql(**mysql_settings)
        self.assertTrue(self.compare_databases(mysql_settings, 'test_vlan.json'))
    
if __name__ == '__main__':
    unittest.main()
