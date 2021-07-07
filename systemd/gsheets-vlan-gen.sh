#!/bin/bash
# Script to be run by cron or systemd timer, to periodically
# run, using Docker, dhcp_config_generator.py, and copy the new
# configuration to ISC DHCPd configuration directory.
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

# Configuration parameters
VOLNAME="gsheets-vlan-gen"
DHCP_CONF_DIR="/etc/dhcp/reservations/"

# Get a new config 
/usr/bin/docker run --rm -v ${VOLNAME}:/var/lib/dhcp-config-gen gsheets-vlan-gen -v

# Copy the config to the DHCPd configuration dir, making a backup of old files
cp -b --suffix=".old" /var/lib/docker/volumes/${VOLNAME}/_data/*.conf ${DHCP_CONF_DIR}

# Test the config
/usr/sbin/dhcpd -t
if [ $? -ne 0 ]; then
	echo "Configuration has errors, aborting..."
	exit 1
fi

# Restart ISC DHCPd server
/usr/bin/systemctl restart isc-dhcp-server.service

# Clean exit
exit 0