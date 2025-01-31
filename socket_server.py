import socket
import threading
import json
from utils import get_chat_history  # Function to fetch chat history

def handle_client_connection(client_socket):
    """Handle incoming client requests to retrieve chat history using user ID."""
    try:
        while True:
            user_id_bytes = client_socket.recv(1024)  # Receive user ID as byte data
            if not user_id_bytes:  # If no data is received, break
                break

            user_id = user_id_bytes.decode('utf-8')  # Decode the received bytes
            chat_history = get_chat_history(user_id)  # Fetch chat history for the user

            # Prepare and send response
            response = json.dumps(chat_history) if chat_history else json.dumps({'error': 'User ID not found or no chat history available.'})
            client_socket.send(response.encode('utf-8'))  # Send the response
    except Exception as e:
        print(f"Error handling client: {e}")
    finally:
        client_socket.close()  # Ensure the connection is closed

def start_websocket_server(host='0.0.0.0', port=5001):
    """Start the WebSocket server to listen for incoming connections."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen(5)  # Maximum number of queued connections
    print(f"Server is listening on {host}:{port}")

    while True:
        client_socket, addr = server.accept()  # Accept a new incoming connection
        print(f"Accepted connection from {addr}")
        client_handler = threading.Thread(target=handle_client_connection, args=(client_socket,))
        client_handler.start()  # Start a new thread to handle the client