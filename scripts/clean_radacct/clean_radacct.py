#!/usr/bin/env python3
# Clean the radacct table in the MySQL FreeRADIUS database.
#
# This script has been ispired by: https://github.com/FreeRADIUS/dialup-admin/blob/master/bin/clean_radacct and
# https://github.com/FreeRADIUS/dialup-admin/blob/master/bin/truncate_radacct.
#
# In a nutshell, removes the stale connections, older than a certain amount of days, and it removes
# all connections older than another amount of days.
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

import json
import argparse
import logging
import logging.handlers
import mysql.connector
import datetime
   
# Parse command line arguments
cli_parser = argparse.ArgumentParser(description="Clean the RADIUS accounting table.")
cli_parser.add_argument("-d", "--mysql-settings",
                       help="JSON-formatted MySQL settings.", metavar="JSON_MYSQL_SETTINGS", default="mysql_settings.json")
cli_parser.add_argument("-s", "--days-stale",
                       help="Number of days to keep stale connections.", default=30, type=int)
cli_parser.add_argument("-m", "--maximum-days",
                       help="Maximum number of days to keep connections.", default=90, type=int)
cli_parser.add_argument("-l", "--log-file",
                       help="Log file.", default="output.log")     
cli_parser.add_argument("-v", "--verbose",
                       help="Be verbose.", action='store_true')                                             
args = cli_parser.parse_args()

# Set up logging
log = logging.getLogger('log')
log.setLevel(logging.INFO)
handler = logging.handlers.TimedRotatingFileHandler(args.log_file, when='W0', backupCount=10)
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s:%(message)s'))
log.addHandler(handler)
if args.verbose:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s:%(message)s'))
    log.addHandler(handler)

# Get current local time
time_now = datetime.datetime.now()

# Load MySQL settings, open connection and cursor
with open(args.mysql_settings, 'r') as f:
    mysql_settings = json.load(f)
cnx = mysql.connector.connect(**mysql_settings)
cur = cnx.cursor()

# Delete old stale connections
cur.execute('DELETE FROM radacct WHERE acctstoptime IS NULL AND acctstarttime < %s',
           (time_now - datetime.timedelta(days=args.days_stale),))
if args.verbose:
    log.info('Deleted {} stale connections.'.format(cur.rowcount))

# Delete old connections
cur.execute('DELETE FROM radacct WHERE acctstoptime < %s AND acctstoptime IS NOT NULL',
           (time_now - datetime.timedelta(days=args.maximum_days),))
if args.verbose:
    log.info('Deleted {} old connections.'.format(cur.rowcount))

# Commit all changes
cnx.commit()

# Close all
cur.close()
cnx.close()
