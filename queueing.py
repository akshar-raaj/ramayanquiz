import pika
import json

from pika.exceptions import StreamLostError
import pika.exceptions

from constants import RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USER, RABBITMQ_PASSWORD


rabbit_connection = None


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
    channel.queue_declare(queue=queue_name, durable=True)
    data = json.dumps({'module_name': module_name, 'function_name': function_name, 'args': args})
    channel.basic_publish(exchange='',
                          routing_key=queue_name,
                          body=data,
                          properties=pika.BasicProperties(delivery_mode=pika.DeliveryMode.Persistent))
    channel.close()
    print(f" [x] Published {data}")


@retry_with_new_connection
def publish_basic(queue_name: str, body: str):
    connection = get_rabbit_connection()
    channel = connection.channel()
    channel.queue_declare(queue_name, durable=True)
    channel.basic_publish('', queue_name, body=body)
    print(f"[x] Published {body} to {queue_name}")
