# Dockerfile to run vlan_config_generator
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

FROM python:alpine
LABEL maintainer="d.pilori@inrim.it"
VOLUME ["/var/lib/vlan-config-gen"]

# Copy Google credentials for gspread
RUN mkdir -p /root/.config/gspread
COPY service_account.json /root/.config/gspread/service_account.json

# Create program dir and copy files
WORKDIR /usr/src/vlan-config-gen
COPY vlan_config_generator.py vlan.py requirements.txt ./

# Install requirements
RUN pip install --no-cache-dir -r requirements.txt

# Execute program
ENTRYPOINT ["python", "./vlan_config_generator.py", \
            "-o", "/var/lib/vlan-config-gen", \
            "-l", "/var/lib/vlan-config-gen/output.log", \
            "-c", "/var/lib/vlan-config-gen/list_vlans.json", \
            "-d", "/var/lib/vlan-config-gen/mysql_settings.json"]
