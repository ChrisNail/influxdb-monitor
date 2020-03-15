import configparser
import subprocess
from influxdb import InfluxDBClient
import wmi

CPU = 'cpu'
HDD = 'hdd'
GPU = 'gpu'

hostname = subprocess.check_output(['hostname'], stderr=subprocess.STDOUT).decode().strip()

def __get_database_client():
    config = configparser.ConfigParser()
    config['InfluxDB'] = {
        'host': 'localhost',
        'port': 8086,
        'database': 'monitoring'
    }
    config.read('monitor.ini')

    host = config['InfluxDB']['host']
    port = int(config['InfluxDB']['port'])
    database_name = config['InfluxDB']['database']

    client = InfluxDBClient(host=host, port=port)
    client.switch_database(database_name)

    return client

def __get_temperature_reading(sensor):
    reading = { 'measurement': 'temperature' }
    reading['tags'] = { 'host': hostname }
    reading['fields'] = { 'value': sensor.Value }

    parent = sensor.Parent.split('/')
    if CPU in parent[1]:
        reading['tags']['device'] = CPU
        reading['tags']['number'] = parent[2]
        reading['tags']['core'] = sensor.Index
    if HDD in parent[1]:
        reading['tags']['device'] = HDD
        reading['tags']['number'] = parent[2]
    if GPU in parent[1]:
        reading['tags']['device'] = GPU
        reading['tags']['number'] = parent[2]
        reading['tags']['core'] = sensor.Index
    if 'lpc' in parent[1]:
        reading['tags']['device'] = 'motherboard'
        reading['tags']['number'] = sensor.Index

    return reading

def __get_fan_reading(sensor):
    reading = { 'measurement': 'fan' }
    reading['tags'] = { 'host': hostname, 'number': (sensor.Index + 1) }
    reading['fields'] = { 'speed': sensor.Value }

    parent = sensor.Parent.split('/')
    if 'lpc' in parent[1]:
        reading['tags']['device'] = 'motherboard'
    if GPU in parent[1]:
        reading['tags']['device'] = GPU

    return reading

def __get_voltage_reading(sensor):
    reading = { 'measurement': 'voltage' }
    reading['tags'] = { 'host': hostname, 'name': sensor.Name }
    reading['fields'] = { 'value': round(sensor.Value, 2) }

    return reading

def __get_load_reading(sensor):
    reading = { 'tags': { 'host': hostname } }

    if CPU in sensor.Parent:
        reading['measurement'] = CPU
        reading['tags']['core'] = sensor.Index
        reading['fields'] = { 'load': round(sensor.Value, 2) }
    elif HDD in sensor.Parent:
        reading['measurement'] = 'storage'
        reading['tags']['device'] = sensor.Parent.split('/')[2]
        reading['fields'] = { 'used_space': round(sensor.Value, 2) }

    return reading

def __get_clock_reading(sensor):
    reading = { 'measurement': 'clock' }
    reading['tags'] = { 'host': hostname, 'name': sensor.Name }
    reading['fields'] = { 'speed': round(sensor.Value, 2) }

    if CPU in sensor.Parent:
        reading['tags']['device'] = CPU
    elif GPU in sensor.Parent:
        reading['tags']['device'] = GPU

    return reading

def __get_power_reading(sensor):
    reading = { 'measurement': 'power' }
    reading['tags'] = { 'host': hostname, 'name': sensor.Name }
    reading['fields'] = { 'watts': round(sensor.Value, 2) }

    return reading

reading_list = []
memory_reading = { 'measurement': 'memory', 'tags': { 'host': hostname }, 'fields': {} }

hardwareMonitor = wmi.WMI(namespace='root\OpenHardwareMonitor')
sensor_list = hardwareMonitor.Sensor()
for sensor in sensor_list:
    if sensor.SensorType == 'Temperature':
        reading_list.append(__get_temperature_reading(sensor))
    elif sensor.SensorType == 'Fan':
        reading_list.append(__get_fan_reading(sensor))
    elif sensor.SensorType == 'Voltage':
        reading_list.append(__get_voltage_reading(sensor))
    elif sensor.SensorType == 'Load' and ('cpu' in sensor.Parent or 'hdd' in sensor.Parent):
        reading_list.append(__get_load_reading(sensor))
    elif sensor.SensorType == 'Clock':
        reading_list.append(__get_clock_reading(sensor))
    elif sensor.SensorType == 'Data' and 'ram' in sensor.Parent:
        if 'Available' in sensor.Name:
            memory_reading['fields']['free_memory'] = round(sensor.Value * 1000)
        elif 'Used' in sensor.Name:
            memory_reading['fields']['used_memory'] = round(sensor.Value * 1000)

reading_list.append(memory_reading)
client = __get_database_client()
client.write_points(reading_list)