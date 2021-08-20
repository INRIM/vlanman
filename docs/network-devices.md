# Configuration of network devices

## ArubaOS-CX switches authentication
This guide will give a "recipe" to configure AAA (authentication, authorization and accounting)
using the RADIUS server configured in [radius.md](radius.md). The user/device is authenticated with:

- Mac address;
- 802.1x EAP.

Each user is assigned to a different VLAN, based on the RADIUS attribute `Tunnel-Private-Group-ID`.

### Base configuration
Start by configuring the RADIUS servers:

```
radius-server host radius.example.com key plaintext secret
aaa accounting port-access start-stop group radius
```

Then, enable Mac and 802.1x authentication:

```
aaa authentication port-access dot1x authenticator             
    enable                                                     
aaa authentication port-access mac-auth                        
    enable                                                     
```

In the case of issues with the RADIUS server, set a static VLAN where the clients will be inserted:

```
port-access role fallback                                      
    vlan access 1                                            
```

For each port, configure AAA:

```
interface 1/1/1
    aaa authentication port-access auth-precedence mac-auth dot1x
    aaa authentication port-access auth-priority dot1x mac-auth
    aaa authentication port-access critical-role fallback
    aaa authentication port-access dot1x authenticator
        max-eapol-requests 2
        max-retries 1
        discovery-period 5
        enable
    aaa authentication port-access mac-auth
        enable
```

This snippet will configure both Mac authentication and 802.1x. If user enables and uses 802.1x, Mac authentication is ignored. This
is useful when a specific user wants to go on a different VLAN compared to the VLAN assigned to the Mac address.

### Variations

#### Only Mac authentication

When only Mac authentication is needed, the configuration can be simplified to:

```
interface 1/1/1
    aaa authentication port-access critical-role fallback
    aaa authentication port-access mac-auth
        enable
```

#### Multiple Mac addresses per port

A single port can have multiple Mac addresses. For instance, the user may be running virtual machines, or it is connected an unmanaged switch.
In this case, there are two options:

1. Enable *device authentication*. In this case, when a single device is successfully authenticated, then the port is considered open, and 
   all clients will be allowed.
2. Increase the maximum number of allowed clients (default: 1).

For the first option:

```
interface 1/1/1
    aaa authentication port-access auth-mode device-mode
```

and for the second:

```
interface 1/1/1
    aaa authentication port-access client-limit 10
```

## MikroTik DHCP server
It is useful to have a DHCP server that supports contacting a RADIUS server to get the lease information.
Unfortunately, on Linux, the only viable solution is [ISC Kea](https://www.isc.org/kea/) with the premium plugins, which cost
an insane amount of money.

Therefore, a good choice of a DHCP server is a [MikroTik](https://mikrotik.com/) device, since MikroTik's RouterOS DHCP server
fully supports a RADIUS server. For this guide, I assume a [RB1100AHx4](https://mikrotik.com/product/rb1100ahx4) router, even though
the guide can be applied to potentially any RouterOS device, including CHR virtual machines.

For this guide we'll assume that the MikroTik device has IP `10.0.0.2` and the RADIUS server, also used for logging, `10.0.0.1`.

### Mikrotik initial setup
1. Start by configuring *Rsyslog* remote logging for audit purposes. On the MikroTik device set:

```bash
/system logging action
set [find name=remote] remote=10.0.0.1
/system logging
add action=remote topics=dhcp,!debug
```

Then, on the *Rsyslog* server (it can be the RADIUS server, or another):

`/etc/rsyslog.d/60-mikrotik-dhcp-server.conf`:
```
$template Dhcp1Log, "/var/log/mikrotik/dhcp1.log"
:fromhost-ip, isequal, "10.0.0.2" -?Dhcp1Log
& stop
```

`/etc/rsyslog.conf`:
```
module(load="imudp")
input(type="imudp" port="514")
$AllowedSender UDP, 10.0.0.2/32
```

`/etc/logrotate.d/mikrotik-dhcp`:
```
/var/log/mikrotik/*.log {
        rotate 30
        daily
        create
        compress
        missingok
        notifempty
}
```

Create the directory `/var/log/mikrotik`, set the permissions, and restart `rsyslogd`:
```bash
mkdir /var/log/mikrotik
chown -R syslog.adm /var/log/mikrotik
systemctl restart rsyslog
```

Make sure that the firewall doesn't block *rsyslog* (UDP port 514). For instance with `ufw`:
```bash
ufw allow proto udp from 10.0.0.2 to any port 514
```

2. Configure the RADIUS server on the MikroTik device:
```bash
/radius
add address=10.0.0.1 secret="secret" service=dhcp
```
Remember to also add this device, along with the shared secret, to the `clients.conf` in the FreeRADIUS configuration.

### For each VLAN

For each VLAN, the MikroTik device acts as a remote DHCP server. The ArubaOS-CX switch, which is the gateway of the network,
acts as a DHCP relay, that relays the information to the server. With this settings, the MikroTik device can be regularly connected to a single VLAN.

Assuming VLAN `100`, with subnet `10.1.0.0/24`, a possible configuration can be:

1. Add a DHCP pool, if needed, for dynamic clients.
```bash
/ip pool
add name=vlan100_pool ranges=10.1.0.10-10.1.0.20
```

2. Set the DHCP network information
```
/ip dhcp-server network
add address=10.1.0.0/24 comment="VLAN100" dns-server=8.8.8.8,8.8.4.4 domain=example.com gateway=10.1.0.1 ntp-server=193.204.114.232,193.204.114.233
```

3. Create and enable the DHCP server
```
/ip dhcp-server
add address-pool=vlan100_pool interface=ether1 name=vlan100-server relay=10.1.0.1 use-radius=yes disabled=no
```

4. Set the DHCP relay on the ArubaOS-CX switch, which acts as gateway.
```
interface vlan 100
    ip address 10.1.0.1/24
    ip helper-address 10.0.0.2
```

### DHCP failover

To set a failover, you can configure another MikroTik device and set the ``delay-threshold``, so that the DHCP server answers only
unanswered requests after this amount of time.

1. Add the DHCP pool and network, exactly as the primary DHCP server:
```bash
/ip pool
add name=vlan100_pool ranges=10.1.0.10-10.1.0.20
/ip dhcp-server network
add address=10.1.0.0/24 comment="VLAN100" dns-server=8.8.8.8,8.8.4.4 domain=example.com gateway=10.1.0.1 ntp-server=193.204.114.232,193.204.114.233
```

2. Add the DHCP server by setting the delay:
```bash
/ip dhcp-server
add address-pool=vlan100_pool interface=ether1 name=vlan100-server relay=10.1.0.1 use-radius=yes disabled=no authoritative=after-10sec-delay delay-threshold=5s
```

## References
- https://help.mikrotik.com/docs/display/ROS/DHCP#DHCP-DHCPServer
- https://wiki.mikrotik.com/wiki/Manual:System/Log
- https://asp.arubanetworks.com/