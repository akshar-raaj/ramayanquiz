import pika
import json


QUEUE_NAME = 'translate-hindi'

connection = pika.BlockingConnection(pika.ConnectionParameters('127.0.0.1'))
channel = connection.channel()

channel.queue_declare(queue=QUEUE_NAME, durable=True)


def publish(module_name: str, function_name: str, args: list):
    data = json.dumps({'module_name': module_name, 'function_name': function_name, 'args': args})
    channel.basic_publish(exchange='',
                        routing_key=QUEUE_NAME,
                        body=data)
    print(f" [x] Published {data}")
