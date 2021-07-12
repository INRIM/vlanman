# FreeRADIUS and MySQL configuration

Unfortunately, [FreeRADIUS](https://freeradius.org/)'s documentation is quite poor. The configuration on this page
was taken from different sources, and it can be improved.

This guide assumes an [Ubuntu Server 20.04 LTS](https://ubuntu.com/server) distribution, but it can be easily applied
to any other distribution.

## General architecture

FreeRADIUS is used as an AAA server for the network equipment. The data is provided by:

- A MySQL database, for Mac address authentication;
- A LDAP directory, for optional 802.1x authentication with EAP.
This guide assumes tha the LDAP server is already installed and configured.

## MySQL configuration

Install MySQL server

```bash
sudo apt install mysql-server
```

Then add a database and a user for FreeRADIUS, by typing the following commands in the `mysql` shell as `root` user:

```sql
CREATE DATABASE radius;
CREATE USER 'radius'@'localhost' IDENTIFIED BY 'password';
GRANT SELECT ON radius.* TO 'radius'@'localhost';
GRANT ALL on radius.radacct TO 'radius'@'localhost';
GRANT ALL on radius.radpostauth TO 'radius'@'localhost';
FLUSH PRIVILEGES;
```

### MySQL replica

Add tutorial to enable native MySQL replica...


## FreeRADIUS configuration

First, install FreeRADIUS:

```bash
sudo apt install freeradius freeradius-mysql
```

The configuration is split into different files in the directory `/etc/freeradius/3.0`. To have a working configuration, edit the following files.

### MySQL schema

First, load the MySQL FreeRADIUS schema:

```bash
mysql radius < /etc/freeradius/3.0/mods-config/sql/main/mysql/schema.sql
```

### `radiusd.conf`

To have a log of all authentications, set the parameter auth to ON:

```
...
auth = yes
...
```

### `proxy.conf`
We don't proxy any information. Just add the local realm, in the case the users log in with your local realm (e.g. `user@example.com`).

```
proxy server {
   default_fallback = no 
}

realm LOCAL {
}

realm NULL {
}

realm example.com {
}
```

and comment out the rest of the lines.

### `clients.conf`

Set the clients (network equiment) that will connect to the RADIUS server. For example:
```
client test_switch {
   	ipaddr = 192.0.2.1
	secret = mysecret
	nas_type = other
	virtual_server = example 
}
```

### Modules

Now it's time to enable and configure the `sql` and (optionally) the `ldap` plugins.

```bash
cd mods-enabled
ln -s ../mods-available/sql .
ln -s ../mods-available/ldap .
```
The configuration of the `ldap` module is out of the scope of this guide. For the `sql` module:

#### `mods-enabled/sql`:

```
sql {
    dialect = "mysql"
    driver = "rlm_sql_${dialect}"
    server = "localhost"
    port = 3306
    login = "radius"
    password = "password"  
}
```
If TLS is desired, uncomment and set the TLS settings lines.

### Virtual servers

We'll need two virtual server. A base virtual server, `example`, with the main configuration. If EAP authentication
(for 802.1x) is enabled, then an `example-inner-tunnel` virtual server is also configured.

### Main virtual server

This configuration is taken from the `default` example, with some modifications.
`sites-available/example`:

```
server example {
listen {
	type = auth
	ipaddr = *
	port = 0

	limit {
	      max_connections = 16
	      lifetime = 0
	      idle_timeout = 30
	}
}

listen {
	ipaddr = *
	port = 0
	type = acct

	limit {
	}
}

listen {
	type = auth
	ipv6addr = ::	# any.  ::1 == localhost
	port = 0
	limit {
	      max_connections = 16
	      lifetime = 0
	      idle_timeout = 30
	}
}

listen {
	ipv6addr = ::
	port = 0
	type = acct

	limit {
	}
}

authorize {
	filter_username
	filter_password
	preprocess
	auth_log
	suffix

    # If no EAP, assume Mac authentication
    # Then: PAP or CHAP authentication, SQL database
	if (!EAP-Message) {
		-sql
		pap
		chap 

	} else {
    # If EAP, then retrieve user from LDAP and use EAP authentication    
		ldap
		pap
		mschap
		chap
	
		eap {
			ok = return
			updated = return
		}
	}
}

authenticate {
	Auth-Type PAP {
		pap
	}

	Auth-Type CHAP {
		chap
	}

	Auth-Type EAP {
		eap
	}
}


preacct {
	preprocess
	acct_counters64

	update request {
	  	&FreeRADIUS-Acct-Session-Start-Time = "%{expr: %l - %{%{Acct-Session-Time}:-0} - %{%{Acct-Delay-Time}:-0}}"
	}

	acct_unique
	suffix
}

accounting {
	-sql
}


session {
}


post-auth {
	if (session-state:User-Name && reply:User-Name && request:User-Name && (reply:User-Name == request:User-Name)) {
		update reply {
			&User-Name !* ANY
		}
	}
	update {
		&reply: += &session-state:
	}

        update reply {
                        Tunnel-Type := VLAN
                        Tunnel-Medium-Type := IEEE-802
        }

	remove_reply_message_if_eap

	Post-Auth-Type REJECT {
		attr_filter.access_reject

		eap

		remove_reply_message_if_eap
	}

	Post-Auth-Type Challenge {
	}
}

pre-proxy {
}

post-proxy {
	eap
}
}
```

and, then, optionally:
`sites-available/example-inner-tunnel`:

```
server example-inner-tunnel {

	authorize {
		filter_username

		if ("%{request:User-Name}" =~ /^(.*)@(.*)/) {
			update request {
				Stripped-User-Name := "%{1}"
				Realm := "%{2}"
			}
		}

		auth_log
		eap

		ldap
		if ((ok || updated) && User-Password) {
			update {
				control:Auth-Type := ldap
			}
		}



		mschap
		pap
	}

	authenticate {
		Auth-Type PAP {
			pap
		}
		Auth-Type MS-CHAP {
			mschap
		}
		Auth-Type LDAP {
			ldap
		}

		eap
	}

	post-auth {
		reply_log
		Post-Auth-Type REJECT {
			attr_filter.access_reject
			reply_log

			update outer.session-state {
				&Module-Failure-Message := &request:Module-Failure-Message
			}
		}
	}

	post-proxy {
		eap
	}
}
```

Enable the servers, deleting the default ones

```bash
cd sites-enabled
rm *
ln -s ../sites-available/example .
ln -s ../sites-available/example-inner-tunnel .
systemctl restart freeradius
```