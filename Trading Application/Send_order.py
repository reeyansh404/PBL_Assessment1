import pika
import json
import sys
from datetime import datetime

def send_order():
    if len(sys.argv) != 6:
        print("Usage: python send-order.py <username> <port> <SIDE> <quantity> <price>")
        print("Example: python send-order.py Alice 5672 BUY 100 49.0")
        return

    username = sys.argv[1]
    port = int(sys.argv[2])
    side = sys.argv[3].upper()
    quantity = int(sys.argv[4])
    price = float(sys.argv[5])

    order = {
        'username': username,
        'side': side,
        'quantity': quantity,
        'price': price,
        'timestamp': datetime.now().isoformat()
    }

    order_json = json.dumps(order)

    try:
        print("Connecting to rabbitmq....")
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='localhost', port=port)
        )
        print("Connected")
        channel = connection.channel()
        print("Channel created")
        channel.queue_declare(queue='orders', durable=True)
        print('Queue declared')

        channel.basic_publish(
            exchange='',
            routing_key='orders',
            body=order_json,
            properties=pika.BasicProperties(
                delivery_mode=2
            )
        )

        print(f"Order sent successfully: {order}")
        connection.close()

    except Exception as e:
        print(f"Failed to connect or send order: {e}")

if __name__ == "__main__":
    send_order()
