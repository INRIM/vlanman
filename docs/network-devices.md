# Configuration of network devices

## ArubaOS-CX switches
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

## References
- https://help.mikrotik.com/docs/display/ROS/DHCP#DHCP-DHCPServer
- https://asp.arubanetworks.com/