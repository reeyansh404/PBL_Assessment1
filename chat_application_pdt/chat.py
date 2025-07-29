# Chat GUI with RabbitMQ - Polling Version (No Threading Issues)

import datetime
import uuid
import json

try:
    import tkinter as tk
    from tkinter import scrolledtext, messagebox, simpledialog
except ModuleNotFoundError as e:
    raise ImportError("Tkinter is not installed or not available in this Python environment.") from e

try:
    import pika
except ModuleNotFoundError as e:
    raise ImportError("Pika (RabbitMQ client) is not installed. Install it via pip install pika.") from e

class ChatApplication:
    def __init__(self, root):
        self.root = root
        self.root.title("Chat Application")
        self.root.geometry("500x400")

        # Get username
        self.username = simpledialog.askstring("Username", "Enter your username:", initialvalue="User")
        if not self.username:
            self.username = f"User_{uuid.uuid4().hex[:4]}"
        
        self.root.title(f"Chat Application - {self.username}")
        self.user_id = uuid.uuid4().hex

        self.message_area = scrolledtext.ScrolledText(root, height=20, width=60)
        self.message_area.pack(padx=10, pady=10)

        self.entry_field = tk.Entry(root, width=50)
        self.entry_field.pack(padx=10, pady=5)
        self.entry_field.bind('<Return>', lambda event: self.send_message())

        button_frame = tk.Frame(root)
        button_frame.pack(padx=10, pady=5)

        self.send_button = tk.Button(button_frame, text="Send", command=self.send_message)
        self.send_button.pack(side=tk.LEFT, padx=5)

        self.status_label = tk.Label(root, text="Connecting...", fg="orange")
        self.status_label.pack(pady=5)

        # Connection variables
        self.connection = None
        self.channel = None
        
        # Each user gets their own unique queue
        self.my_queue = f"chat_user_{self.user_id}"
        
        self.setup_connection()
        
        # Start polling for messages (no threading)
        self.poll_messages()

    def setup_connection(self):
        try:
            # Simple connection parameters
            params = pika.ConnectionParameters(
                host='localhost',
                heartbeat=0,  # Disable heartbeat
                connection_attempts=3,
                retry_delay=1,
                socket_timeout=5
            )
            
            self.connection = pika.BlockingConnection(params)
            self.channel = self.connection.channel()
            
            # Declare fanout exchange
            self.channel.exchange_declare(
                exchange='chat_broadcast',
                exchange_type='fanout',
                durable=False
            )
            
            # Create our unique queue
            self.channel.queue_declare(
                queue=self.my_queue,
                durable=False,
                exclusive=False,
                auto_delete=True
            )
            
            # Bind our queue to the fanout exchange
            self.channel.queue_bind(
                exchange='chat_broadcast',
                queue=self.my_queue
            )
            
            self.status_label.config(text="Connected", fg="green")
            
        except Exception as e:
            self.status_label.config(text="Connection Failed", fg="red")
            messagebox.showerror("Connection Error", f"Failed to connect: {e}")

    def send_message(self):
        message = self.entry_field.get().strip()
        if not message:
            return
            
        if not self.connection or self.connection.is_closed:
            messagebox.showerror("Error", "Not connected to RabbitMQ")
            return
            
        try:
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            
            # Create message with sender info
            message_data = {
                'sender_id': self.user_id,
                'username': self.username,
                'message': message,
                'timestamp': timestamp
            }
            
            # Publish to fanout exchange
            self.channel.basic_publish(
                exchange='chat_broadcast',
                routing_key='',
                body=json.dumps(message_data)
            )
            
            # Show our own message immediately
            self.message_area.insert(tk.END, f"You [{timestamp}]: {message}\n")
            self.message_area.see(tk.END)
            self.entry_field.delete(0, tk.END)
            
        except Exception as e:
            self.status_label.config(text="Send Failed", fg="red")
            messagebox.showerror("Send Error", f"Failed to send: {e}")
            # Try to reconnect
            self.reconnect()

    def poll_messages(self):
        """Poll for messages without threading"""
        if not self.connection or self.connection.is_closed:
            # Try to reconnect
            self.reconnect()
            self.root.after(1000, self.poll_messages)
            return
            
        try:
            # Check for messages (non-blocking)
            method, properties, body = self.channel.basic_get(queue=self.my_queue, auto_ack=True)
            
            if method:
                # We got a message
                try:
                    message_data = json.loads(body.decode())
                    
                    # Skip our own messages
                    if message_data.get('sender_id') != self.user_id:
                        formatted_msg = f"{message_data['username']} [{message_data['timestamp']}]: {message_data['message']}"
                        self.message_area.insert(tk.END, formatted_msg + "\n")
                        self.message_area.see(tk.END)
                        
                except Exception as e:
                    print(f"Message processing error: {e}")
            
        except Exception as e:
            print(f"Polling error: {e}")
            self.status_label.config(text="Connection Issue", fg="orange")
            
        # Schedule next poll
        self.root.after(100, self.poll_messages)  # Poll every 100ms

    def reconnect(self):
        """Try to reconnect"""
        try:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
        except:
            pass
            
        self.status_label.config(text="Reconnecting...", fg="orange")
        
        try:
            self.setup_connection()
        except Exception as e:
            print(f"Reconnect failed: {e}")

    def on_closing(self):
        """Clean shutdown"""
        try:
            if self.connection and not self.connection.is_closed:
                # Clean up our queue
                try:
                    self.channel.queue_delete(queue=self.my_queue)
                except:
                    pass
                self.connection.close()
        except:
            pass
            
        self.root.destroy()

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = ChatApplication(root)
        root.protocol("WM_DELETE_WINDOW", app.on_closing)
        root.mainloop()
    except Exception as e:
        print(f"Application error: {e}")