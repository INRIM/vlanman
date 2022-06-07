#!/usr/bin/env python3
# Script to synchronize a FreeRADIUS database and and ISC DHCPd configuration from
# Google Sheet files.
#
# Copyright (c) 2021-2022 Istituto Nazionale di Ricerca Metrologica <d.pilori@inrim.it>
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

from vlan import Vlan
import json
import argparse
import logging
import logging.handlers

# Function to convert a dict to a Vlan object
def get_vlan_from_json(dct):
    """ Simple hook to convert a dictionary from JSON a Vlan object. """
    return Vlan(**dct)
   
# Parse command line arguments
cli_parser = argparse.ArgumentParser(description="Script to synchronize a FreeRADIUS database and and ISC DHCPd configuration from Google Sheet files.")
cli_parser.add_argument('--dhcp', help='Generate ISC DHCPd configuration files.', action='store_true')
cli_parser.add_argument('--no-radius', help='Do not synchronize with FreeRADIUS database.', action='store_true')
cli_parser.add_argument("-o", "--output-dir",
                       help="Output dir for DHCPd configuration files.", metavar="DIR", default=".")
cli_parser.add_argument("-c", "--list-vlans",
                       help="JSON-formatted list of VLANs.", metavar="JSON_LIST_VLANS", default="list_vlans.json")
cli_parser.add_argument("-d", "--mysql-settings",
                       help="JSON-formatted MySQL settings.", metavar="JSON_MYSQL_SETTINGS", default="mysql_settings.json")
cli_parser.add_argument("-l", "--log-file",
                       help="Log file.", default="output.log")     
cli_parser.add_argument("-v", "--verbose",
                       help="Be verbose.", action='store_true')
cli_parser.add_argument("--specific-vlans",
                       help="Process only a list of VLANs (space separated).", metavar='VLAN_ID', nargs='+', type=int)                                       
args = cli_parser.parse_args()

# Set up logging
vlan_logger = logging.getLogger('vlan_logger')
vlan_logger.setLevel(logging.INFO)
handler = logging.handlers.TimedRotatingFileHandler(args.log_file, when='W0', backupCount=10)
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s:%(message)s'))
vlan_logger.addHandler(handler)
if args.verbose:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s:%(message)s'))
    vlan_logger.addHandler(handler)

# Load configuration file
with open(args.list_vlans, 'r') as f:
    list_vlan = json.load(f, object_hook=get_vlan_from_json)

# For all VLANS
for v in list_vlan:
    # Verify if list of specific VLANs is given
    if args.specific_vlans and (v.vlan_id not in args.specific_vlans):
        continue

    # Get data from Google Sheets
    try:
         v.retrieve_data()
    except Exception as exc:
        logging.error('Unable to retrieve data from Google for VLAN {} due to error "{}"'.format(v.vlan_id, exc))

    # Generate ISC DHCPd configuration files
    if args.dhcp:
        try:
            v.generate_dhcp_config()
            v.dump_to_dhcpd(out_dir=args.output_dir)
            vlan_logger.info('Successfully generated DHCP config for VLAN {}'.format(v.vlan_id))
        except Exception as exc:
            vlan_logger.error('Skipping ISC DHCP config of VLAN {} due to {} error: "{}".'.format(v.vlan_id, type(exc).__name__, exc))

    # Synchronize with FreeRADIUS MySQL database
    if not args.no_radius:
        try:
            v.generate_radius_config(mark_errors=True)
            with open(args.mysql_settings, 'r') as f:
                mysql_settings = json.load(f)
            v.dump_to_radius_mysql(**mysql_settings, print_function=vlan_logger.info)
            vlan_logger.info('Successfully synchronized RADIUS db for VLAN {}'.format(v.vlan_id))
        except Exception as exc:
            vlan_logger.error('Skipping RADIUS database sync of VLAN {} due to {} error: "{}".'.format(v.vlan_id, type(exc).__name__, exc))
