import pika
import json

from pika.exceptions import StreamLostError

from constants import RABBITMQ_HOST


rabbit_connection = None
QUEUE_NAME = 'translate-hindi'


def get_rabbit_connection(force=False):
    global rabbit_connection
    if rabbit_connection is None or force:
        rabbit_connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
    return rabbit_connection


def retry_with_new_connection(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except StreamLostError:
            print("handling closed TCP connection error")
            get_rabbit_connection(force=True)
            return func(*args, **kwargs)
    return wrapper


@retry_with_new_connection
def publish(module_name: str, function_name: str, args: list, queue_name: str = QUEUE_NAME):
    connection = get_rabbit_connection()
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    data = json.dumps({'module_name': module_name, 'function_name': function_name, 'args': args})
    channel.basic_publish(exchange='',
                          routing_key=QUEUE_NAME,
                          body=data)
    print(f" [x] Published {data}")
