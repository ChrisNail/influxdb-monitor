# Linux InfluxDB Monitor
A python script to read sensor data on a Linux machine and insert it into an InfluxDB.

## Requirements
- InfluxDB
- Linux program `lm-sensors`
- Python Modules:
  - `configparser`
  - `subprocess`
  - `influxdb`

## Available Config Options
```
[InfluxDB]
host = localhost
port = 8086
database = monitoring
```
