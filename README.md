# Dependencies
* paramiko
* ncclient
* PyYAML
* Pika
* Jinja2

If pip is installed, just run `pip install -r pip_dependencies`.


# Description
This module provides classes in `devices.py` (for now, just `Junos`) to interact with network devices.
Classes defined in `devices.py` use NETCONF to represent their respective devices as python objects.

The `Junos` object has the following immutable attributes:

* object.serial
* object.model
* object.ifaces

In addition to the immutable attributes, the following mutable one are also available:

* object.ntp_servers
* object.snmp_communities
* object.hostname

Any mutable attribute can be redefined and written to the network device `update()` method. 


## Using the Library
Using Junos device object

```
>>> from device import Junos
>>> conn_params = {
...     'host': '192.168.56.2',
...     'port': '22',
...     'username': 'vagrant',
...     'key_filename': 'vagrant.key',
...     'hostkey_verify': False,
...     'timeout': 5,
...     'device_params': {'name': 'junos'}
... }
>>> dev_obj = Junos(conn_params)
>>> dev_obj.hostname
vsrx-01
>>> dev_obj.serial
57520414eea4
>>> dev_obj.ntp_servers
['10.0.2.1', '10.0.2.2']
>>> dev_obj.ntp_servers = ['10.0.2.3']
>>> dev_obj.ntp_servers
['10.0.2.3']
>>> dev_obj.update(commit=True)
True
```

Device object is idempotent.

```
>>> from device import Junos
>>> conn_params = {
...     'host': '192.168.56.2',
...     'port': '22',
...     'username': 'vagrant',
...     'key_filename': 'vagrant.key',
...     'hostkey_verify': False,
...     'timeout': 5,
...     'device_params': {'name': 'junos'}
... }
>>> dev_obj = Junos(conn_params)
>>> dev_obj.hostname
vsrx-01
>>> dev_obj.hostname = "vsrx-01"
>>> dev_obj.update()
False
```


## Using the Script
`conf_time.py` takes the following optional arguments:
```
-h, --help                show this help message and exit
--input INPUT, -i         INPUT YAML input file. (Default: input.yaml)
--verify, -v              Verify hostkey. (Default: False)
--timeout TIMEOUT, -t     TIMEOUT Timeout. (Default: 5s)
--port PORT, -p PORT      TCP port. (Default: 22)
--username USERNAME, -u   USERNAME Username. (Default: vagrant)
--key KEY, -k KEY         Keyfile for PKI authentication. 
                          (Default: vagrant/vagrant.key)
--threads THREADS         Number of threads to start. (Default: None)
--rabbitmq [RABBITMQ]     Send to RabbitMQ URL. 
                          (Default: ampq://guest:guest@localhost:5672/)
```
It returns the object's properties as JSON.


### Input
The input file is `input.yaml` by default. Each mapping is defined with the network devices
hostname or IPv4/6 address as its key and consisting of various values defining its properties.

```yaml
192.168.56.2:
  hostname: vsrx-01
  ntp_servers:
    - 10.0.2.2
    - 10.0.2.1
  snmp_communities:
    - private
    - public
"fe80::800:27ff:fe00:2%vboxnet0":
  hostname: vsrx01
  ntp_servers:
    - 10.0.2.2
    - 10.0.2.1
  snmp_communities:
    - private
    - public
``` 


### Scaling
By default, the program runs single-threaded. To use multiple threads, use the --threads *n* option.
`conf_time.py` also supports sending jobs to a RabbitMQ server. `worker.py` is a very simple example
of a consumer. 


# Tests
Unit tests in `tests.py` cover possible use cases of the library and run against static test data in 
the test_data directory. Tests do not cover the script as it's intended for use with live devices. 
However, a Vagrantfile is included that will start an environment the default `input.yaml` can run against.
Assuming you're using the Virtualbox provider, just issue a `vagrant up` in the root directory to begin three 
vSRX instances connected to vboxnet0 with IPs of 192.168.56.2-4.