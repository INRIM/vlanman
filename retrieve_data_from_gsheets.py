#!/usr/bin/env python3
# retrieve_data_from_gsheets.py
# Simple script to retrieve a list of 
# IP addresses, MAC addresses and hostnames
# from a Google Sheet file. Data is saved in a JSON file.

# Copyright (c) 2021 Dario Pilori, INRiM <d.pilori@inrim.it>
# SPDX-License-Identifier: MIT

import gspread
import json

gc = gspread.service_account()

sh = gc.open('LAB_MAGMODEL_VLAN701')
records = sh.sheet1.get_all_records()

with open("vlan701.json", "w") as f:
    json.dump(records, f, indent=4)
   
