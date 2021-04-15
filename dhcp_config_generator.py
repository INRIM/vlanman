#!/usr/bin/env python3
# Script to automatically generate a set of DHCPd configuration files.
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
cli_parser = argparse.ArgumentParser(description="Generate a set of ISC DHCPd configuration files from Google Sheets files.")
cli_parser.add_argument("-o", "--output-dir",
                       help="Output dir for DHCPd configuration files.", metavar="DIR", default=".")
cli_parser.add_argument("-c", "--config-json",
                       help="JSON-formatted configuration file.", metavar="JSON_FILE", default="list_vlans.json")
cli_parser.add_argument("-l", "--log-file",
                       help="Log file.", default="output.log")     
cli_parser.add_argument("-v", "--verbose",
                       help="Be verbose.", action='store_true')                                             
args = cli_parser.parse_args()

# Set up logging
dhcp_logger = logging.getLogger('dhcp_logger')
dhcp_logger.setLevel(logging.INFO)
handler = logging.handlers.TimedRotatingFileHandler(args.log_file, when='W0', backupCount=10)
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s:%(message)s'))
dhcp_logger.addHandler(handler)
if args.verbose:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s:%(message)s'))
    dhcp_logger.addHandler(handler)

# Load configuration file
with open(args.config_json, 'r') as f:
    list_vlan = json.load(f, object_hook=get_vlan_from_json)

# For all VLANS
for v in list_vlan:
    # Get info from Google Drive
    try:
    #    v.retrieve_data()
         pass
    except Exception as exc:
        logging.error('Unable to retrieve data from Google for VLAN {} due to error "{}"'.format(v.vlan_id, exc))

    # Generate and save configuration
    try:
    #    v.generate_dhcp_config()
        v.generate_dhcp_config('test/test_vlan.json')
        v.dump_to_dhcpd(out_dir=args.output_dir)
        dhcp_logger.info('Successfully parsed VLAN {}'.format(v.vlan_id))
    except Exception as exc:
        dhcp_logger.error('Skipping vlan {} due to {} error: "{}".'.format(v.vlan_id, type(exc).__name__, exc))

