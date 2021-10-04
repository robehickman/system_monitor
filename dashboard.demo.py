import time
from system_monitor.client import *

config = {
    'hosts' : {
        'local'      : ['127.0.0.1',  12345]
    }
}

init_client(config)

while client_active():

    remote_data = get_remote_data()

    row = []

    # -------------
    col = []

    col += render_disk_usage   (remote_data, 'local')
    col += render_memory_usage (remote_data, 'local')
    col += render_cpu_usage    (remote_data, 'local')
    col += render_network_usage(remote_data, 'local')

    # -------------
    row += vertical_stack(col)

    render(horizontal_stack(row))

    time.sleep(0.5)
