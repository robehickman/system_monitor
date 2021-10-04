import os, struct, time, json
import socket, shutil
import psutil 

from threading import Thread, Lock

with open('/etc/system_monitor.json', 'r') as f:
    config = json.loads(f.read())


# ===============================================
# Utility functions to enumerate disks,
# mounted file systems etc
# ===============================================

# ===============================================
def get_physical_disks():
    data = os.popen('lsblk --json').read()
    res = json.loads(data)
    all_devices = res['blockdevices']

    devices = []
    for dev in all_devices:
        if dev['name'][0:4] == 'nvme' or dev['name'][0:2] == 'sd':
            devices.append(dev['name'])

    return devices

# ===============================================
def get_smart_status(block_device_name):

    # -------------------
    cmd = 'smartctl -json -H -A /dev/' + block_device_name
    data = os.popen(cmd).read()
    res = json.loads(data)

    value = {'passed' : res['smart_status']['passed']}

    if "ata_smart_attributes" in res:
        result = {}
        for item in res["ata_smart_attributes"]["table"]:
            result[item['name']] = item['raw']['string']

        value['attrs'] = result

    elif "nvme_smart_health_information_log" in res:
        value['attrs'] = res["nvme_smart_health_information_log"]

    return value

# ===============================================
def get_file_systems():

    file_systems = []
    for part in psutil.disk_partitions():
        if '/snap' not in part.mountpoint:
            file_systems.append(part.mountpoint)
    return file_systems


# ===============================================
# All of the system monitoring runs in
# independent threads so they can be updated
# at different time intervals.
# ===============================================
data_cache = {}
threadLock = Lock()


# ===============================================
def update_smart_data(check_interval):
    global threadLock, data_cache

    physical_disks = get_physical_disks()

    while True:
        print('update smart data')

        output = {}

        for disk in physical_disks:
            output[disk] = get_smart_status(disk)

        threadLock.acquire()
        data_cache['smart_data'] = output
        threadLock.release()

        time.sleep(check_interval)


# ===============================================
def update_file_system_utilisation(check_interval):
    global threadLock, data_cache


    file_systems    = get_file_systems()

    while True:
        output = {}

        for file_system in file_systems:
            usage = shutil.disk_usage(file_system)
            output[file_system] = usage.used / usage.total


        threadLock.acquire()
        data_cache['disk_use'] = output
        threadLock.release()

        time.sleep(check_interval)


# ===============================================
def update_memory_use(check_interval):
    global threadLock, data_cache

    while True:
        # Memory
        mem = psutil.virtual_memory()

        threadLock.acquire()
        data_cache['memory'] = {
            'available' : mem.total,
            'used'      : mem.used
        }
        threadLock.release()

        time.sleep(check_interval)

# ===============================================
def update_cpu_use(check_interval):
    global threadLock, data_cache

    while True:
        cpu_use = psutil.cpu_percent(interval=check_interval, percpu=True)

        threadLock.acquire()
        data_cache['cpu'] = cpu_use
        threadLock.release()


# ===============================================
network_recv_last = None
network_sent_last = None

def update_network_use(check_interval):
    global threadLock, data_cache, network_recv_last, network_sent_last

    while True:
        network = psutil.net_io_counters(pernic=False)

        if network_recv_last == None:
            network_recv_last = network.bytes_recv
            network_sent_last = network.bytes_sent

        recv = network.bytes_recv - network_recv_last
        sent = network.bytes_sent - network_sent_last

        threadLock.acquire()
        data_cache['network'] = {
            'sent' : sent / 1024,
            'recv' : sent / 1024,
        }
        threadLock.release()

        network_recv_last = network.bytes_recv
        network_sent_last = network.bytes_sent


        time.sleep(check_interval)

# ===============================================
# Server connection handler
# ===============================================
pool = []

if 'smart_data' in config['check']:
    pool.append(
        Thread(target=update_smart_data,
               args=(config['check']['smart_data'],)))

if 'file_system_utilisation' in config['check']:
    pool.append(
                Thread(target=update_file_system_utilisation,
                       args=(config['check']['file_system_utilisation'],)))

if 'memory_use' in config['check']:
    pool.append(
        Thread(target=update_memory_use,
               args=(config['check']['memory_use'],)))

if 'cpu_use' in config['check']:
    pool.append(
        Thread(target=update_cpu_use,
               args=(config['check']['cpu_use'],)))

if 'network_use' in config['check']:
    pool.append(
        Thread(target=update_network_use,
               args=(config['check']['network_use'],)))

[t.start() for t in pool]


# =================================================
# =================================================
def conection_handler(c, addr):
    while True:
        threadLock.acquire()
        data = json.dumps(data_cache).encode()
        threadLock.release()

        c.send(struct.pack("!i", len(data)))
        c.send(data)

        time.sleep(config['send_frequency'])



# =================================================
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((config['bind_address'], config['bind_port']))
s.listen(5)

while True:
    c, addr = s.accept()
    c.settimeout(60)
    t = Thread(target = conection_handler,args = (c,addr))
    pool.append(t)
    t.start()

