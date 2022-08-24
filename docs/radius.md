# FreeRADIUS and MySQL configuration

Unfortunately, [FreeRADIUS](https://freeradius.org/)'s documentation is quite poor. The configuration on this page
was taken from different sources, and it can be improved.

This guide assumes an [Ubuntu Server 22.04 LTS](https://ubuntu.com/server) distribution, but it can be easily applied
to any other distribution.

## General architecture

FreeRADIUS is used as an AAA server for the network equipment. The data is provided by a **MySQL** database, for Mac address authentication;

## MySQL configuration

Install MySQL server

```bash
sudo apt install mysql-server
```

Then add a database and a user for FreeRADIUS and a full-privilege user, by typing the following commands in the `mysql` shell as `root` user:

```sql
CREATE DATABASE radius;
CREATE USER 'radius'@'localhost' IDENTIFIED BY 'password';
GRANT SELECT ON radius.* TO 'radius'@'localhost';
GRANT ALL on radius.radacct TO 'radius'@'localhost';
GRANT ALL on radius.radpostauth TO 'radius'@'localhost';
FLUSH PRIVILEGES;
```

This user will have very limited privileges. Add then a fully-privileged user for administration and for the script
that updates the database:

```sql
CREATE USER 'gsheets-gen'@'localhost' IDENTIFIED BY 'password';
GRANT ALL PRIVILEGES ON radius.* TO 'gsheets-gen'@'localhost';
```

### MySQL replica

It is always useful to have a secondary RADIUS server, with a full replica of the MySQL server.
For this, we can leverage MySQL integrated replica. Remember that, for the replica configurations,
the two servers must be *100% clean*, i.e. no data is present. If not so, please check MySQL
documentation for guidance.

### Main server

Start by editing the server configuration file `/etc/mysql/mysql.conf.d/mysqld.cnf`:

```
# Comment out this line
# bind-address = 127.0.0.1

# Set a different server-id on each server
server-id               = 1
# Binary logs expire after 30 days
binlog_expire_logs_seconds      = 2592000
max_binlog_size   = 100M
# Create binary log for radius DB
binlog_do_db            = radius
# Enable GTID-based replica
gtid_mode = ON
enforce-gtid-consistency = ON
```

Restart the server:

```bash
systemctl restart mysql
```

Then, create a replication user, that can connect only from the replica (`radius2.example.com`) and has minimal privileges.
We use SSL to secure the connection, even though we don't check for the certificates.

```sql
CREATE USER 'replica'@'radius2.example.com' IDENTIFIED BY 'password' REQUIRE SSL;
GRANT REPLICATION SLAVE ON *.* TO 'replica'@'radius2.example.com';
```

### Replica

Then create the same radius database and add the radius user (read-only!).

```sql
CREATE DATABASE radius;
CREATE USER 'radius'@'localhost' IDENTIFIED BY 'password';
GRANT SELECT ON radius.* TO 'radius'@'localhost';
FLUSH PRIVILEGES;
```

Also in this case, edit the server configuration file `/etc/mysql/mysql.conf.d/mysqld.cnf`:

```
server-id               = 2
binlog_expire_logs_seconds      = 2592000
max_binlog_size   = 100M
binlog_do_db            = radius
gtid_mode = ON
enforce-gtid-consistency = ON

# Relay log is important in the case of issues with the replica server
relay-log = /var/log/mysql/mysql-relay-bin.log

# Keep this only on first configuration, then, if it works, remove this line!
skip_slave_start = ON
```

Restart the server:

```bash
systemctl restart mysql
```

Then enable replica:

```sql
CHANGE REPLICATION SOURCE TO
     >     SOURCE_HOST = host,
     >     SOURCE_PORT = port,
     >     SOURCE_USER = user,
     >     SOURCE_PASSWORD = password,
     >     SOURCE_AUTO_POSITION = 1;
START REPLICA;
```

If everything works, then remove the `skip_slave_start` line on the configuration file. The FreeRADIUS configuration is identical, with 
the exception that the accounting lines are missing (the database on the replica is read-only).

## FreeRADIUS configuration

The FreeRADIUS version contained in the repositories is quite old, and it's best to get directly the latest version from the repositories: https://networkradius.com/packages/.


Then, install FreeRADIUS:

```bash
sudo apt install freeradius freeradius-mysql
```

The configuration is split into different files in the directory `/etc/freeradius`. To have a working configuration, edit the following files.

### MySQL schema

First, load the MySQL FreeRADIUS schema:

```bash
mysql radius < /etc/freeradius/mods-config/sql/main/mysql/schema.sql
```

### `radiusd.conf`

To have a log of all authentications, set the parameter auth to ON:

```
...
auth = yes
...
```

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

### Mac canonicalization

This guide assumes that the Mac address is given by network equiment as a simple hex string, without any separator
(e.g. `0123456789ab`). Some equipment may use different standards, which cannot be configured. In this case,
a simple policy will rewrite any Mac address to this standard. Create the file `policy.d/mac-canonicalization`:

```
mac-addr-regexp = '([0-9a-f]{2})[^0-9a-f]?([0-9a-f]{2})[^0-9a-f]?([0-9a-f]{2})[^0-9a-f]?([0-9a-f]{2})[^0-9a-f]?([0-9a-f]{2})[^0-9a-f]?([0-9a-f]{2})'

rewrite_mac_username {
	if (&User-Name && (&User-Name =~ /^${policy.mac-addr-regexp}([^0-9a-f](.+))?$/i)) {
		update request {
			&User-Name := "%{tolower:%{1}%{2}%{3}%{4}%{5}%{6}}"
		}
		updated
	}
	else {
		noop
	}
}
```

### Modules

Now it's time to enable and configure the `sql` module.

```bash
cd mods-enabled
ln -s ../mods-available/sql .
```

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

	rewrite_mac_username
	-sql
	pap
	chap 
}

authenticate {
	Auth-Type PAP {
		pap
	}

	Auth-Type CHAP {
		chap
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

	# Set VLAN
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
}
}
```

Enable the server, deleting the default ones

```bash
cd sites-enabled
rm *
ln -s ../sites-available/example .
systemctl restart freeradius
```

## References

- https://www.digitalocean.com/community/tutorials/how-to-set-up-replication-in-mysql
- https://dev.mysql.com/doc/refman/8.0/en/replication-gtids-howto.html
- https://wiki.freeradius.org/guide/SQL-HOWTO-for-freeradius-3.x-on-Debian-Ubuntu
- https://wiki.freeradius.org/guide/mac-auth
- https://docs.eduroam.it/configurazione/freeradius.html
- https://help.mikrotik.com/docs/display/ROS/DHCP#DHCP-DHCPServer