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

class TestVlan(unittest.TestCase):
    def compare_databases(self, mysql_settings, json_in):
        return True

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
