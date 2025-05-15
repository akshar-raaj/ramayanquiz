import pika
import json
import logging

from pika.exceptions import StreamLostError
import pika.exceptions

from constants import RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USER, RABBITMQ_PASSWORD


rabbit_connection = None


logger = logging.getLogger(__name__)


def get_rabbit_connection(force=False):
    global rabbit_connection
    if rabbit_connection is None or force:
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
        rabbit_connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT, credentials=credentials))
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


def health():
    connection = get_rabbit_connection()
    channel = connection.channel()
    try:
        channel.queue_declare('process-question', passive=True)
        return True
    except pika.exceptions.ChannelClosedByBroker:
        # Even if the queue is not found.
        # It's okay as long as we are able to connect to the RabbitMQ Host.
        return True


@retry_with_new_connection
def publish(module_name: str, function_name: str, args: list, queue_name: str):
    connection = get_rabbit_connection()
    channel = connection.channel()
    # A durable queue, will survive a server restart or a server crash
    channel.queue_declare(queue=queue_name, durable=True)
    data = json.dumps({'module_name': module_name, 'function_name': function_name, 'args': args})
    # Publishing to a Direct exchange with the queue routing_key.
    # It will ensure that the exchange routes to the queue with the same name as routing key.
    channel.basic_publish(exchange='',
                          routing_key=queue_name,
                          body=data,
                          properties=pika.BasicProperties(delivery_mode=pika.DeliveryMode.Persistent))
    channel.close()
    logger.info(f"Published {data} to {queue_name}")


@retry_with_new_connection
def publish_basic(queue_name: str, body: str):
    connection = get_rabbit_connection()
    channel = connection.channel()
    channel.queue_declare(queue_name, durable=True)
    channel.basic_publish('', queue_name, body=body)
    print(f"[x] Published {body} to {queue_name}")
