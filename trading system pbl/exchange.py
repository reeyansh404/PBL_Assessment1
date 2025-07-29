import pika               # For RabbitMQ messaging
import json               # To decode order messages
import sys                # For command-line argument handling
from datetime import datetime  # For timestamps

# Dictionary to hold order books for each stock
order_books = {}

# Helper function to print a nicely formatted incoming order
def print_order_received(order):
    """Prints the details of a received order."""
    print("\n--- New Order Received ---")
    print(f"User: {order['username']}")
    print(f"Stock: {order['stock']}")
    print(f"Side: {order['side']}")
    print(f"Quantity: {order['quantity']}")
    print(f"Price: ${order['price']:.2f}")
    print(f"Timestamp: {order['timestamp']}")
    print("--------------------------\n")

# Helper function to print a nicely formatted executed trade
def print_trade_executed(trade):
    """Prints the details of an executed trade."""
    print("\n=== TRADE EXECUTED ===")
    print(f"{trade['buyer']} buys {trade['quantity']} shares of {trade['stock']} from {trade['seller']} at ${trade['price']:.2f}")
    print(f"Timestamp: {trade['timestamp']}")
    print("======================\n")

# Core matching function
def match_order(new_order):
    """
    Tries to match a new incoming order with existing opposite-side orders
    from the same stock's order book. Supports partial matching and multiple trades.
    """
    stock = new_order.get("stock", "XYZ")  # Default stock if not specified
    side = new_order["side"]

    # Initialize order book for stock if this is the first order for it
    if stock not in order_books:
        order_books[stock] = {"BUY": [], "SELL": []}

    # Determine which side of the order book we're matching against
    opposite_side = "SELL" if side == "BUY" else "BUY"
    matching_orders = order_books[stock][opposite_side]

    # Sort opposite-side orders for best price matching (price priority)
    if opposite_side == "SELL":
        matching_orders.sort(key=lambda o: o['price'])  # Match BUY with lowest sell
    else:
        matching_orders.sort(key=lambda o: -o['price']) # Match SELL with highest buy

    trades = []  # To collect all resulting trades
    remaining_qty = new_order["quantity"]

    # Try to match with existing orders while quantity remains
    while matching_orders and remaining_qty > 0:
        existing_order = matching_orders[0]

        # Check if prices match according to trading logic
        price_match = (
            (side == "BUY" and new_order["price"] >= existing_order["price"]) or
            (side == "SELL" and new_order["price"] <= existing_order["price"])
        )

        if not price_match:
            break  # Stop if no suitable match is found

        # Trade quantity is the minimum of remaining quantities
        trade_qty = min(remaining_qty, existing_order["quantity"])

        # Create the trade record
        trade = {
            "stock": stock,
            "buyer": new_order["username"] if side == "BUY" else existing_order["username"],
            "seller": existing_order["username"] if side == "BUY" else new_order["username"],
            "price": existing_order["price"] if side == "BUY" else new_order["price"],
            "quantity": trade_qty,
            "timestamp": datetime.now().isoformat()
        }
        trades.append(trade)

        # Update quantities
        remaining_qty -= trade_qty
        existing_order["quantity"] -= trade_qty

        # If matched order is fully filled, remove it from the book
        if existing_order["quantity"] == 0:
            matching_orders.pop(0)

    # If any quantity of the new order remains unmatched, store it in the book
    if remaining_qty > 0:
        new_order["quantity"] = remaining_qty
        order_books[stock][side].append(new_order)

    return trades  # Return list of trades executed (could be empty)

# Entry point for the exchange system
def main():
    """Main function to connect to RabbitMQ and start listening for orders."""
    if len(sys.argv) != 2:
        print("Usage: python exchange.py <port>")
        return

    port = int(sys.argv[1])  # RabbitMQ port passed as argument

    try:
        # Connect to RabbitMQ
        connection = pika.BlockingConnection(
            pika.ConnectionParameters('localhost', port=port, ssl_options=None)
        )
        channel = connection.channel()

        # Declare necessary queues
        channel.queue_declare(queue='orders', durable=True)
        channel.queue_declare(queue='trades', durable=True)

        print("Exchange is running and waiting for orders...")

        # Define callback to handle incoming orders
        def callback(ch, method, properties, body):
            order = json.loads(body.decode())  # Decode JSON message
            print_order_received(order)        # Log received order

            trades = match_order(order)        # Match and process trades
            for trade in trades:
                trade_json = json.dumps(trade)
                # Publish trade result to 'trades' queue
                channel.basic_publish(exchange='', routing_key='trades', body=trade_json)
                print_trade_executed(trade)    # Log trade result

        # Begin consuming from 'orders' queue
        channel.basic_consume(queue='orders', on_message_callback=callback, auto_ack=True)
        channel.start_consuming()

    except KeyboardInterrupt:
        print("Exchange shutting down gracefully.")
    except Exception as e:
        print(f"Exchange failed: {e}")

# Launch program
if __name__ == "__main__":
    main()
