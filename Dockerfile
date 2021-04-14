# Dockerfile to run dhcp_config_generator
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

FROM python:alpine
LABEL maintainer="d.pilori@inrim.it"
VOLUME ["/var/lib/dhcp-config-gen"]

# Copy credentials to Google
RUN mkdir -p /root/.config/gspread
COPY service_account.json /root/.config/gspread/service_account.json

# Create program dir and enter
WORKDIR /usr/src/dhcp-config-gen
COPY dhcp_config_generator.py ./
COPY requirements.txt ./
COPY vlan.py ./
COPY list_vlans.json ./

# Install requirements
RUN pip install --no-cache-dir -r requirements.txt

# Execute program
ENTRYPOINT ["python", "./dhcp_config_generator.py", "-o", "/var/lib/dhcp-config-gen", "-l", "/var/lib/dhcp-config-gen/output.log"]

