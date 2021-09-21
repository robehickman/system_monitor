from system_monitor.client import *


config = {
    'hosts' : {
        'local'      : ['127.0.0.1',  12345]
    }
}


init_client(config)

while client_active():

    remote_data = get_remote_data()

    horisontal_stack = []

    # Localhost system info
    col1 = []

    # ----------------------------------
    col1.append(heading('Percentage disk used'))

    output = []

    for device, used in remote_data['local']['disk_use'].items():
        output.append([device + ': ', str(round(used * 100))])

    col1.append(
        table(output)
    )


    # ----------------------------------
    col1.append(
        table([[
            'Memory:', 
            str(round(remote_data['local']['memory']['used'] / 1048576))  + ' MB of ' + str(round(remote_data['local']['memory']['available'] / 1048576)) + ' MB'
        ]])
    )


    # ----------------------------------
    col1.append(heading('CPU'))

    i = 1

    output = []
    for usage in remote_data['local']['cpu']:
        output.append([
            'cpu' + str(i) + ': ',
            str(usage)
        ])

        i += 1

    col1.append(
        table(output)
    )


    # -------------
    col1.append(heading('Network'))

    col1.append(
        table([
            [
                'Recv:',
                str(round(remote_data['local']['network']['recv']))
            ],
            [
                'Sent:',
                str(round(remote_data['local']['network']['sent']))
            ]
        ])
    )
    

    # =====================================
    horisontal_stack.append({
        'type' : 'vertical_stack',
        'data' : col1
    })



    # =====================================
    render([{
        'type' : 'horizontal_stack', 
        'data' : horisontal_stack
    }])


