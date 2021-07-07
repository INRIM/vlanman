# Create a test MySQL database.
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

import argparse
import mysql.connector

# Parse command line arguments
cli_parser = argparse.ArgumentParser(description="Create a test MySQL database.")
cli_parser.add_argument("-u", "--user",
                       help="MySQL user", default="radius")
cli_parser.add_argument("-p", "--password",
                       help="MySQL password", default="password")
cli_parser.add_argument("-s", "--host",
                       help="MySQL host", default="mysql")
cli_parser.add_argument("-d", "--database",
                       help="MySQL database name", default="radius")
args = cli_parser.parse_args()

# Connect to MySQL
cnx = mysql.connector.connect(database=args.database, user=args.user, password=args.password, host=args.host)
cur = cnx.cursor()

# Load MySQL schema
with open('mysql_freeradius3_schema.sql', 'r') as f:
    sql_file = f.read()

# all SQL commands (split on ';')
sql_cmds = sql_file.split(';')

# Execute every sql_cmds from the input file
for cmd in sql_cmds:
    # This will skip and report errors
    # For example, if the tables do not yet exist, this will skip over
    # the DROP TABLE commands
    try:
        if cmd.rstrip() != '':
            cur.execute(cmd)
    except ValueError as msg:
        print('Command skipped: {}'.format(msg))

# Commit these changes
cnx.commit()

# Close MySQL
cur.close()
cnx.close()
