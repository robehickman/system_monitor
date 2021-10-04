# System Monitor

A network enabled system monitor and dashboard construction kit (a la conky) that can monitor data from multiple systems at once in a single interface.

Note that this system was designed to be tunneled over an overlay network like wireguard or nebula, and has no native authentication or encryption. DO NOT bind the server to a public network interface!


## Setup

Install:

```
sudo pip3 install .
```


Create server config in /etc/system\_monitor.json

Fields under 'check' specify what system information should be sent to a connected client. The value associated with each key is the frequency (in seconds) to poll this resource and update the cached data.

```
{
    "send_frequency" : 4,
    "bind_address"   : "127.0.0.1",
    "bind_port"      : 12345,

    "check" : {
        "file_system_utilisation" : 100, # The second value here is polling frequency
        "memory_use"              : 1,
        "cpu_use"                 : 1,
        "network_use"             : 1
    }
}
```


Run the server. Note that this can also be run from a systemd unit file to make it start on boot.

```
monitor_server.py
```


Configure and run the client. See dashboard.demo.py


```
python3 ./dashboard.demo.py
```

