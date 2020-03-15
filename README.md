# Linux InfluxDB Monitor
A python script to read sensor data and insert it into an InfluxDB server.

## Requirements
- InfluxDB
- Python Modules:
  - `configparser`
  - `subprocess`
  - `influxdb`
### Linux Requirements
- Program `lm-sensors`
### Windows Requirements
- Python Module `wmi`

## Available Config Options
The script looks for `monitor.ini` in the root folder
```
[InfluxDB]
host = localhost
port = 8086
database = monitoring
```
