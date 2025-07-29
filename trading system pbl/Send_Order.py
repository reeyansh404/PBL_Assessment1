# Import necessary modules
import pika                  # For RabbitMQ communication
import json                  # To format the message as JSON
import sys                   # For command-line arguments
from datetime import datetime  # To timestamp each order

# Function to print the sent order in a readable format
def print_order_sent(order):
    """Prints the details of the sent order."""
    print("\n--- Order Sent ---")
    print(f"User: {order['username']}")
    print(f"Stock: {order['stock']}")
    print(f"Side: {order['side']}")  # BUY or SELL
    print(f"Quantity: {order['quantity']}")
    print(f"Price: ${order['price']:.2f}")
    print(f"Timestamp: {order['timestamp']}")
    print("------------------\n")

# Function to construct and send an order message to RabbitMQ
def send_order():
    """
    Builds and sends an order to the RabbitMQ 'orders' queue.
    Expects: <username> <port> <stock> <BUY/SELL> <quantity> <price>
    """
    # Validate number of arguments
    if len(sys.argv) != 7:
        print("Usage: python3 send_order.py <username> <port> <stock> <SIDE> <quantity> <price>")
        print("Example: python3 send_order.py John 5672 XYZ BUY 100 50.0")
        return

    # Extract command-line arguments
    username = sys.argv[1]
    port = int(sys.argv[2])
    stock = sys.argv[3].upper()        # Convert to uppercase (e.g., "xyz" -> "XYZ")
    side = sys.argv[4].upper()         # BUY or SELL
    quantity = int(sys.argv[5])        # Number of shares
    price = float(sys.argv[6])         # Price per share

    # Input validation
    if side not in ("BUY", "SELL") or quantity <= 0 or price <= 0:
        print("Invalid input: Side must be BUY or SELL, and quantity/price must be positive.")
        return

    # Create the order as a dictionary
    order = {
        'username': username,
        'stock': stock,
        'side': side,
        'quantity': quantity,
        'price': price,
        'timestamp': datetime.now().isoformat()  # Generate ISO 8601 timestamp
    }

    # Convert the order to a JSON string
    order_json = json.dumps(order)

    try:
        # Connect to RabbitMQ at the specified port
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='localhost', port=port, ssl_options=None)
        )
        channel = connection.channel()

        # Declare the 'orders' queue to ensure it exists
        channel.queue_declare(queue='orders', durable=True)

        # Send the order to the 'orders' queue
        channel.basic_publish(
            exchange='',
            routing_key='orders',
            body=order_json
        )

        # Print the order confirmation to the terminal
        print_order_sent(order)

        # Close the connection
        connection.close()

    except Exception as e:
        # Handle and display connection or sending errors
        print(f"Failed Connection: {e}")

# Run the send_order() function if the script is executed directly
if __name__ == "__main__":
    send_order()
