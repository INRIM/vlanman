# Clean up of RADIUS accounting table
The `radacct` table contains all RADIUS's accounting information. This table can become very large. Therefore,
it is useful to remove all connections older than a certain date, and also stale connections.

## The script
The script [clean_radacct.py](../scripts/clean_radacct/clean_radacct.py) can help. It can be used with the following options:
```bash
$ ./clean_radacct.py -h
usage: clean_radacct.py [-h] [-d JSON_MYSQL_SETTINGS] [-s DAYS_STALE] [-m MAXIMUM_DAYS] [-l LOG_FILE] [-v]

Clean the RADIUS accounting table.

optional arguments:
  -h, --help            show this help message and exit
  -d JSON_MYSQL_SETTINGS, --mysql-settings JSON_MYSQL_SETTINGS
                        JSON-formatted MySQL settings.
  -s DAYS_STALE, --days-stale DAYS_STALE
                        Number of days to keep stale connections.
  -m MAXIMUM_DAYS, --maximum-days MAXIMUM_DAYS
                        Maximum number of days to keep connections.
  -l LOG_FILE, --log-file LOG_FILE
                        Log file.
  -v, --verbose         Be verbose.
```

By default, it removes all connections older than 180 days (6 months), and stale connections older than 35 days. 
The syntax of the MySQL settings JSON file is identical to the `mysql_settings.json` file:
```json
{
    "database": "radius",
    "host": "radius.example.com",
    "password": "password",
    "user": "cleanradacct"
}
```
This script requires a user with `SELECT` and `DELETE` privileges on the `radacct` table. For instance:
```sql
CREATE USER 'cleanradacct'@'myserver.example.com' IDENTIFIED BY 'password';
GRANT SELECT, DELETE ON radius.radacct TO 'cleanradacct'@'myserver.example.com';
```

## Execution with Docker
This script can be directly run, or executed inside a lightweight Docker container. For this purpose, 
an example [Dockerfile](../scripts/clean_radacct/Dockerfile) is provided.

1. Edit the command line options in the [Dockerfile](../scripts/clean_radacct/Dockerfile), if needed (e.g. to set the maximum
   number of days).
2. Create a Docker [volume](https://docs.docker.com/storage/volumes/)
   that contains the logfile `output.log` and the `mysql_settings.json` file:
   ```bash
   docker volume create clean-radacct 
   ```
3. Copy the `mysql_settings.json` to the Docker volume:
   ```bash
   cp mysql_settings.json /var/lib/docker/volumes/clean-radacct/_data
   ```
4. Build the Docker image
   ```bash
   docker build -t clean-radacct .
   ```
5. Once created the image, you can *manually* build the new configurations with the following command:
   ```bash
   docker run --rm -v clean-radacct:/var/lib/clean-radacct clean-radacct
   ```
   The files and the logfile will be created inside the Docker volume, i.e. in `/var/lib/docker/volumes/clean-radacct`.
6. The command written previously can be scripted, e.g. using crontab or a systemd timer.
