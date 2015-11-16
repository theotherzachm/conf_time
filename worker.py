#!/usr/bin/env python
import argparse
import pika
import cPickle as pickle
from run import do_stuff


def arguments():
    parser = argparse.ArgumentParser(
        description='''
            Test
        '''
    )
    parser.add_argument(
        '--queue',
        '-q',
        default='ampq://guest:guest@localhost:5672/%2f',
        help='Connect to RabbitMQ URL'
    )
    return parser.parse_args()

args = arguments()
connection = pika.BlockingConnection(
    pika.URLParameters(args.queue)
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
