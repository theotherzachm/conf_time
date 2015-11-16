#!/usr/bin/python
import argparse
import logging
from multiprocessing import Pool
import json
import cPickle as pickle
import sys
import yaml
from conf_time.device import detect, Junos


def arguments():
    parser = argparse.ArgumentParser(
        description='''
            Uses NETCONF to change network devices.
            Takes YAML input from file specified with -i option.
            Prints device attributes to stdout in JSON. Defaults
            to single-threaded operation but can take advantage of
            multi-threading with --thread n option.
        '''
    )
    parser.add_argument(
        '--input',
        '-i',
        default='input.yaml',
        help='YAML input file. (Default: input.yaml)'
    )
    parser.add_argument(
        '--verify',
        '-v',
        action='store_true',
        help='Verify hostkey. (Default: False)'
    )
    parser.add_argument(
        '--timeout',
        '-t',
        default=5,
        help='Timeout. (Default: 5s)'
    )
    parser.add_argument(
        '--port',
        '-p',
        default=22,
        help='TCP port. (Default: 22)'
    )
    parser.add_argument(
        '--username',
        '-u',
        default='vagrant',
        help='Username. (Default: vagrant)'
    )
    parser.add_argument(
        '--key',
        '-k',
        default='vagrant/vagrant.key',
        help='Keyfile for PKI authentication. (Default: vagrant/vagrant.key)'
    )
    parser.add_argument(
        '--worker',
        '-w',
        action='store_true',
        help='Start as RabbitMQ worker.'
    )
    scale = parser.add_mutually_exclusive_group()
    scale.add_argument(
        '--threads',
        type=int,
        help='Number of threads to start.'
    )
    scale.add_argument(
        '--rabbitmq',
        const='ampq://guest:guest@localhost:5672/%2f',
        nargs='?',
        help='Send to RabbitMQ URL'
    )
    return parser.parse_args()


def do_stuff(host=None, in_device=None, args=None):
    '''
    Instantiates a network device object. Then it sets the
    network device object's attributes with data from the input
    and runs update method. It also pretty-prints the network
    object's properties to JSON before editing/commit.
    '''

    if not host and in_device and args:
        raise TypeError('Missing required arguments.')

    conn_params = {
        'host': host,
        'port': args['port'],
        'username': args['username'],
        'key_filename': args['key'],
        'hostkey_verify': args['verify'],
        'timeout': args['timeout'],
    }

    try:
        device_params = detect(conn_params)
    except Exception as error:
        logging.error('{} - "{}"'.format(
            host,
            error
        ))
        return None

    if device_params.get('name') == 'junos':
        conn_params['device_params'] = device_params
        dev_obj = Junos(conn_params)
        for val_name, val_vars in in_device.iteritems():
            if type(val_vars) is list:
                val_vars = sorted(val_vars)
            if getattr(dev_obj, val_name) != val_vars:
                setattr(dev_obj, val_name, val_vars)
        print json.dumps(dict(dev_obj), indent=4)
        return dev_obj.update(edit=True, commit=True)

    if device_params.get('name') == 'nexus':
        raise NotImplemented('Soon!')


if __name__ == '__main__':
    args = arguments()
    devices = yaml.load(open(args.input, 'r'))

    def ds_wrapper(device):
        return do_stuff(
            host=device[0],
            in_device=device[1],
            args=vars(args),
        )

    if args.threads:
        Pool(args.threads).map(ds_wrapper, devices.iteritems())
        sys.exit(0)
    if args.rabbitmq and not args.worker:
        import pika
        connection = pika.BlockingConnection(
            pika.URLParameters(args.rabbitmq)
        )
        channel = connection.channel()
        channel.queue_declare(queue='netconf')
        for i in devices.items():
            to_worker = i, vars(args)
            channel.basic_publish(
                exchange='',
                routing_key='netconf',
                body=pickle.dumps(to_worker)
            )
        connection.close()
        sys.exit(0)
    if args.rabbitmq and args.worker:
        import pika
        connection = pika.BlockingConnection(
            pika.URLParameters(args.rabbitmq)
        )
        channel = connection.channel()
        channel.queue_declare(queue='netconf')
        print(' [*] Waiting for messages. To exit press CTRL+C')

        def run_do_stuff(ch, method, properties, body):
            r_data = pickle.loads(body)
            return do_stuff(
                host=r_data[0][0],
                in_device=r_data[0][1],
                args=r_data[1]
            )

        channel.basic_consume(
            run_do_stuff,
            queue='netconf',
            no_ack=True
        )
        channel.start_consuming()
    else:
        map(ds_wrapper, devices.items())
        sys.exit(0)
