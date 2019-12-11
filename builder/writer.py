#!/usr/bin/env python

import os
import sys
from time import sleep, strftime
from datetime import datetime
import logging
import json
import pickle

import pika

from greent.util import LoggingUtil
from greent.export import BufferedWriter
from builder.buildmain import setup
from greent.graph_components import KNode, KEdge
from builder.api import logging_config
from pika.exceptions import StreamLostError
import threading

greent_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..')
logger = LoggingUtil.init_logging("builder.writer", level=logging.DEBUG, logFilePath= os.path.join(greent_path,'..','logs','builder.writer'))

greent_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..')
sys.path.insert(0, greent_path)
rosetta = setup(os.path.join(greent_path, 'greent', 'greent.conf'))

writer = BufferedWriter(rosetta)



def callback_wrapper(ch, method, properties, body):
    callback(body)
    ch.basic_ack(method.delivery_tag)

def callback(body):
    # logger.info(f" [x] Received {body}")
    graph = pickle.loads(body)
    if isinstance(graph, str) and graph == 'flush':
        logger.debug('Flushing buffer...')
        writer.flush()
    else:
        for node in graph['nodes']:
            # logger.debug(f'Writing node {node.id}')
            writer.write_node(node)
        for edge in graph['edges']:
            # logger.debug(f'Writing edge {edge.source_id}->{edge.target_id}')
            if 'force' in graph:
                writer.write_edge(edge, force_create= True)
            else:
                writer.write_edge(edge)
    return
    
def setup_consumer(callback = callback):
    # Setup code same as our previous, creating the queue on the channel.
    # Not doing auto_ack incase the channel drops on us and we lose some data that 
    # the channel has picked up but not processed yet.
    logger.info(f' [*] Setting up consumer, creating new connection')
    connection = pika.BlockingConnection(pika.ConnectionParameters(
        heartbeat= 1,
        host=os.environ['BROKER_HOST'],
        virtual_host='builder',
        credentials=pika.credentials.PlainCredentials(os.environ['BROKER_USER'], os.environ['BROKER_PASSWORD'])
    ))
    channel = connection.channel()
    channel.queue_declare(queue='neo4j')
    channel.basic_consume('neo4j', callback, auto_ack=False)
    return channel


def start_consuming(max_retries = 0):    
    # Consumer wrappper tries to connect to the broker for 
    # max_retries then exits. We don't want to loop over and over for ever
    while max_retries != 0:
        print('To exit press CTRL+C')
        try:
            channel = setup_consumer(callback= callback_wrapper)
            logger.info(' [*] Waiting for messages.')
            channel.start_consuming()
        except StreamLostError as error:
            logger.info(f' [x] {error}')
            logger.info(f' [x] channel connection    status: Open = {channel.is_open}')
            if channel.is_open:
                channel.close()
            max_retries -= 1
            logger.info(f" [x] Retrying connection to {os.environ['BROKER_HOST']} : {max_retries} retries left")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="""
    Start the writer that connects to rabbit mq.
    """, formatter_class= argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-r','--retries', help= 'On failing to connect to rabbit mq the writer will tries to reconnect. Put in negative integer for auto allow infinite retries. Default value is -1.', default= -1)
    args = parser.parse_args()
    try:
        max_retries = int(args.retries)
        start_consuming(max_retries=max_retries)
    except Exception as e:
        logger.error(f'[x] An error has occured {e}')
