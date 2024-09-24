#!/usr/bin/env python
import pika
import json
import importlib


QUEUE_NAME = 'translate-hindi'

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='127.0.0.1'))
channel = connection.channel()

channel.queue_declare(queue=QUEUE_NAME, durable=True)
print(' [*] Waiting for messages. To exit press CTRL+C')


def callback(ch, method, properties, body):
    body = body.decode()
    # Expecting the body to be json with the following keys:
    # full function name, args
    try:
        body = json.loads(body)
        assert 'module_name' in body
        assert 'function_name' in body
        assert 'args' in body
    except Exception:
        # Log as an exception
        return None
    module_name = body['module_name']
    function_name = body['function_name']
    args = body['args']
    try:
        module = importlib.import_module(module_name)
    except Exception:
        # Log as an exception
        return None
    try:
        func = getattr(module, function_name)
    except Exception:
        return None
    try:
        func(*args)
    except Exception:
        pass
    print(" [x] Done")
    ch.basic_ack(delivery_tag=method.delivery_tag)


channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)

channel.start_consuming()
