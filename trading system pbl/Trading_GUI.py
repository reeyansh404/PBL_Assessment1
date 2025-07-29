import pika               # For communicating with RabbitMQ
import json               # For decoding trade messages
import threading          # To run RabbitMQ listener without freezing the GUI
import tkinter as tk      # For creating the GUI
from tkinter import ttk   # For using the dropdown (Combobox)

# GUI class to visualize live trades from the 'trades' queue
class TradeGUI:
    """
    TradeGUI is a graphical user interface (GUI) application for monitoring stock trades.

    It connects to a RabbitMQ broker, listens for messages from the 'trades' queue,
    and displays the latest prices and trade history per stock in real-time.
    """

    def __init__(self, master, rabbitmq_host='localhost', port=5672):
        """
        Initializes the GUI layout and sets up background thread for RabbitMQ listening.
        """
        self.master = master
        master.title("Stock Trades Monitor")  # Set window title

        self.latest_prices = {}     # Stores the most recent price per stock (e.g., {'XYZ': 49.0})
        self.trade_history = []     # Stores full trade history received so far

        # Dropdown for selecting stock
        self.stock_var = tk.StringVar()
        self.stock_dropdown = ttk.Combobox(master, textvariable=self.stock_var)
        self.stock_dropdown.pack(pady=10)
        self.stock_dropdown.bind("<<ComboboxSelected>>", self.update_display)

        # Label to show latest price
        self.price_label = tk.Label(master, text="Latest Price: N/A", font=("Helvetica", 16))
        self.price_label.pack(pady=10)

        # Text box to show trade history (last 10 trades)
        self.history_text = tk.Text(master, height=10, width=50)
        self.history_text.pack(padx=10, pady=10)

        # Store RabbitMQ connection parameters
        self.connection_params = pika.ConnectionParameters(host=rabbitmq_host, port=port, ssl_options=None)

        # Start RabbitMQ listening in background thread (so GUI stays responsive)
        threading.Thread(target=self.start_listening, daemon=True).start()

    def start_listening(self):
        """
        Connects to RabbitMQ and listens to the 'trades' queue.
        Each trade is processed and the display is updated accordingly.
        """
        try:
            connection = pika.BlockingConnection(self.connection_params)
            channel = connection.channel()

            # Ensure the queue exists
            channel.queue_declare(queue='trades', durable=True)

            # Callback function that runs every time a new trade is received
            def callback(ch, method, properties, body):
                trade = json.loads(body.decode())  # Convert JSON message to Python dict
                stock = trade.get("stock", "XYZ")  # Default stock to XYZ if not provided
                price = trade.get("price")

                # Update latest price and add trade to history
                self.latest_prices[stock] = price
                self.trade_history.append(trade)

                # Update dropdown values with all known stocks
                stocks = list(self.latest_prices.keys())
                self.master.after(0, lambda: self.stock_dropdown.configure(values=stocks))

                # Auto-refresh display if the selected stock matches the new trade's stock
                if self.stock_var.get() == stock:
                    self.master.after(0, self.update_display)

            # Start listening to the queue with the callback
            channel.basic_consume(queue='trades', on_message_callback=callback, auto_ack=True)
            print("GUI listening to 'trades' queue...")
            channel.start_consuming()

        except Exception as e:
            print(f"RabbitMQ connection error: {e}")

    def update_display(self, event=None):
        """
        Updates the price label and trade history display for the selected stock.
        Triggered when the dropdown selection changes or a matching trade is received.
        """
        stock = self.stock_var.get()
        if not stock:
            self.price_label.config(text="Latest Price: N/A")
            return

        # Show latest price
        price = self.latest_prices.get(stock, "N/A")
        self.price_label.config(text=f"Latest Price for {stock}: ${price}")

        # Filter and show only trades of selected stock (last 10 entries)
        trades = [t for t in self.trade_history if t.get("stock") == stock]
        self.history_text.delete('1.0', tk.END)
        for trade in reversed(trades[-10:]):  # Show most recent first
            self.history_text.insert(tk.END, f"{trade['timestamp']} - {trade['buyer']} bought from {trade['seller']} at ${trade['price']}\n")

# Entry point to run the GUI
def main():
    root = tk.Tk()
    app = TradeGUI(root)
    root.mainloop()

# Only run main if the script is executed directly
if __name__ == "__main__":
    main()
