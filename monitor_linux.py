import configparser
import subprocess
from influxdb import InfluxDBClient

def get_database_client():
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

def process_temps(hostname):
    RAM = 'dimm'
    CPU = 'core'

    def __find_device_number(line):
        return line[-2:]

    def __find_slot_number(line):
        index = line.find(':')
        return line[index-1:index]

    def __find_channel_number(line):
        index = line.lower().find(RAM)
        return line[index-2:index-1]

    def __find_temp(line):
        begin_index = line.find('+') + 1
        end_index = line.find('°')
        text = line[begin_index:end_index]
        return float(text)

    output = subprocess.check_output(['sensors', '-A'], stderr=subprocess.STDOUT).decode()
    lineList = output.splitlines()
    data = []
    device = ""

    for line in lineList:
        if len(line) == 0:
            device = ""
            continue
        if len(device) == 0:
            device = line[line.rfind('-') + 1:]
            continue
        reading = { 'measurement': 'temperature' }
        reading['tags'] = { 'host': hostname }
        if CPU in line.lower():
            reading['tags']['device'] = 'cpu'
            reading['tags']['number'] = __find_device_number(device)
            reading['tags']['core'] = __find_slot_number(line)
        elif RAM in line.lower():
            reading['tags']['device'] = 'ram'
            reading['tags']['channel'] = __find_channel_number(line)
            reading['tags']['slot'] = __find_slot_number(line)
        reading['fields'] = { 'value': __find_temp(line) }
        data.append(reading)
    return data

def process_stats(hostname):
    processHeaders = {
        'r': 'running_processes',
        'b': 'sleeping_processes'
    }

    memoryHeaders = {
        'swpd': 'virtual_memory',
        'free': 'free_memory',
        'buff': 'buffer_memory',
        'cache': 'cache_memory'
    }

    cpuHeaders = {
        'us': 'non-kernel_time',
        'sy': 'kernel_time',
        'id': 'idle_time',
        'wa': 'wait_time',
        'st': 'stolen_time'
    }

    data = [
        {'measurement': 'processes', 'tags': { 'host': hostname }, 'fields': {}},
        {'measurement': 'memory', 'tags': { 'host': hostname }, 'fields': {}},
        {'measurement': 'cpu', 'tags': { 'host': hostname }, 'fields': {}}
    ]


    output = subprocess.check_output(['vmstat', '-w', '-S', 'M'], stderr=subprocess.STDOUT).decode()
    lineList = output.splitlines()
    headerList = lineList[1].split()
    valueList = lineList[2].split()

    for i in range(len(headerList)):
        headerCode = headerList[i]
        if headerCode in processHeaders:
            header = processHeaders[headerCode]
            data[0]['fields'][header] = int(valueList[i])
        if headerCode in memoryHeaders:
            header = memoryHeaders[headerCode]
            data[1]['fields'][header] = int(valueList[i])
        if headerCode in cpuHeaders:
            header = cpuHeaders[headerCode]
            data[2]['fields'][header] = int(valueList[i])

    return data

def process_fans(hostname):
    def __get_speed(str):
        if not str:
            return 0
        
        return int(str)

    output = subprocess.check_output(['sudo', 'ipmitool', 'sdr', 'list', 'full', '-c'], stderr=subprocess.STDOUT).decode()
    lineList = output.splitlines()
    data = []

    for line in lineList:
        if 'FAN' in line:
            fieldList = line.split(',')
            reading = { 'measurement': 'fan' }
            reading['tags'] = {
                'host': hostname,
                'number': fieldList[0].split()[1]
            }
            reading['fields'] = {
                'speed': __get_speed(fieldList[1]),
                'status': fieldList[3]
            }

            data.append(reading)

    return data

hostname = subprocess.check_output(['hostname'], stderr=subprocess.STDOUT).decode().strip()
temp_data = process_temps(hostname)
mem_data = process_stats(hostname)
#fan_data = process_fans(hostname)
client = get_database_client()
client.write_points(temp_data)
client.write_points(mem_data)
#client.write_points(fan_data)
