#!/usr/bin/env python3
"""
LAN Communication Server
Handles multiple clients with video, audio, chat, screen sharing, and file transfer
"""

import socket
import threading
import json
import struct
import time
import os
from datetime import datetime

class LANCommServer:
    def __init__(self, host='0.0.0.0', tcp_port=5555, video_port=5556, audio_port=5557):
        self.host = host
        self.tcp_port = tcp_port
        self.video_port = video_port
        self.audio_port = audio_port
        
        # Client management
        self.clients = {}  # {username: {tcp_socket, address, video_addr, audio_addr}}
        self.clients_lock = threading.Lock()
        
        # Session management
        self.presenter = None
        self.presenter_lock = threading.Lock()
        
        # File sharing
        self.shared_files = {}  # {file_id: {filename, size, data}}
        self.files_lock = threading.Lock()
        
        # Sockets
        self.tcp_socket = None
        self.video_socket = None
        self.audio_socket = None
        
        # Running flag
        self.running = False
        
        print(f"[SERVER] Initializing LAN Communication Server")
        print(f"[SERVER] TCP Port: {tcp_port}, Video Port: {video_port}, Audio Port: {audio_port}")
    
    def start(self):
        """Start all server components"""
        self.running = True
        
        # Start TCP server for control, chat, and file transfer
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_socket.bind((self.host, self.tcp_port))
        self.tcp_socket.listen(10)
        print(f"[TCP] Server listening on {self.host}:{self.tcp_port}")
        
        # Start UDP server for video
        self.video_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.video_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.video_socket.bind((self.host, self.video_port))
        print(f"[VIDEO] UDP server listening on {self.host}:{self.video_port}")
        
        # Start UDP server for audio
        self.audio_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.audio_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.audio_socket.bind((self.host, self.audio_port))
        print(f"[AUDIO] UDP server listening on {self.host}:{self.audio_port}")
        
        # Start handler threads
        threading.Thread(target=self.accept_connections, daemon=True).start()
        threading.Thread(target=self.handle_video_stream, daemon=True).start()
        threading.Thread(target=self.handle_audio_stream, daemon=True).start()
        
        print("[SERVER] All services started successfully")
    
    def accept_connections(self):
        """Accept incoming TCP connections"""
        while self.running:
            try:
                client_socket, address = self.tcp_socket.accept()
                print(f"[TCP] New connection from {address}")
                threading.Thread(target=self.handle_client, args=(client_socket, address), daemon=True).start()
            except Exception as e:
                if self.running:
                    print(f"[TCP] Error accepting connection: {e}")
    
    def handle_client(self, client_socket, address):
        """Handle individual client TCP connection"""
        username = None
        try:
            # Receive registration message
            data = self.recv_message(client_socket)
            if data and data['type'] == 'register':
                username = data['username']
                
                with self.clients_lock:
                    self.clients[username] = {
                        'tcp_socket': client_socket,
                        'address': address,
                        'video_addr': None,
                        'audio_addr': None
                    }
                
                # Send welcome message
                self.send_message(client_socket, {
                    'type': 'welcome',
                    'message': f'Welcome to LAN Communication Server, {username}!',
                    'users': list(self.clients.keys())
                })
                # If someone is already presenting, inform the newly joined user
                with self.presenter_lock:
                    if self.presenter is not None:
                        self.send_message(client_socket, {
                            'type': 'presentation_started',
                            'username': self.presenter
                        })
                
                # Notify all other clients
                self.broadcast_message({
                    'type': 'user_joined',
                    'username': username,
                    'users': list(self.clients.keys())
                }, exclude=username)
                
                print(f"[TCP] User '{username}' registered from {address}")
                
                # Handle client messages
                while self.running:
                    msg = self.recv_message(client_socket)
                    if not msg:
                        break
                    
                    self.process_message(username, msg)
            
        except Exception as e:
            print(f"[TCP] Error handling client {username}: {e}")
        finally:
            # Cleanup
            if username:
                with self.clients_lock:
                    if username in self.clients:
                        del self.clients[username]
                
                # Check if presenter left
                with self.presenter_lock:
                    if self.presenter == username:
                        self.presenter = None
                        self.broadcast_message({
                            'type': 'presentation_stopped',
                            'username': username
                        })
                
                # Notify others
                self.broadcast_message({
                    'type': 'user_left',
                    'username': username,
                    'users': list(self.clients.keys())
                })
                
                print(f"[TCP] User '{username}' disconnected")
            
            try:
                client_socket.close()
            except:
                pass
    
    def process_message(self, username, msg):
        """Process messages from clients"""
        msg_type = msg.get('type')
        
        if msg_type == 'chat':
            # Broadcast chat message
            self.broadcast_message({
                'type': 'chat',
                'username': username,
                'message': msg['message'],
                'timestamp': datetime.now().strftime('%H:%M:%S')
            })
            print(f"[CHAT] {username}: {msg['message']}")
        
        elif msg_type == 'video_register':
            # Register video address
            with self.clients_lock:
                if username in self.clients:
                    self.clients[username]['video_addr'] = tuple(msg['address'])
            print(f"[VIDEO] Registered video address for {username}")
        
        elif msg_type == 'audio_register':
            # Register audio address
            with self.clients_lock:
                if username in self.clients:
                    self.clients[username]['audio_addr'] = tuple(msg['address'])
            print(f"[AUDIO] Registered audio address for {username}")
        
        elif msg_type == 'start_presentation':
            # Start presentation
            with self.presenter_lock:
                if self.presenter is None:
                    self.presenter = username
                    self.broadcast_message({
                        'type': 'presentation_started',
                        'username': username
                    })
                    self.send_to_user(username, {
                        'type': 'presentation_control',
                        'status': 'started'
                    })
                    print(f"[SCREEN] {username} started presenting")
                else:
                    self.send_to_user(username, {
                        'type': 'presentation_control',
                        'status': 'denied',
                        'message': f'{self.presenter} is currently presenting'
                    })
        
        elif msg_type == 'stop_presentation':
            # Stop presentation
            with self.presenter_lock:
                if self.presenter == username:
                    self.presenter = None
                    self.broadcast_message({
                        'type': 'presentation_stopped',
                        'username': username
                    })
                    print(f"[SCREEN] {username} stopped presenting")
        
        elif msg_type == 'screen_frame':
            # Forward screen frame to all clients (INCLUDING sender so they see their own screen)
            with self.presenter_lock:
                if self.presenter == username:
                    self.broadcast_message({
                        'type': 'screen_frame',
                        'username': username,
                        'frame_data': msg['frame_data']
                    })  # No exclude - everyone including presenter sees it
                    print(f"[SCREEN] Broadcasted frame from {username} to all clients")
        
        elif msg_type == 'private_chat':
            # Route private chat to a specific recipient and echo back to sender
            to_user = (msg.get('to') or '').strip()
            text = msg.get('message', '')
            if not to_user or to_user == username:
                return
            print(f"[PM] {username} -> {to_user}: {text}")
            # Deliver to recipient if online
            delivered = False
            canonical_to = None
            with self.clients_lock:
                # Resolve case-insensitive username to the canonical key stored on server
                for key in self.clients.keys():
                    if key.lower() == to_user.lower():
                        canonical_to = key
                        break
                delivered = canonical_to is not None
            if delivered and canonical_to:
                # Broadcast to all; clients will locally filter to show only if
                # they are the sender or the intended recipient. This avoids
                # edge cases with name normalization and ensures delivery.
                self.broadcast_message({
                    'type': 'private_chat',
                    'from': username,
                    'to': canonical_to,
                    'message': text,
                    'timestamp': datetime.now().strftime('%H:%M:%S')
                })
                print(f"[PM] delivered to {canonical_to} (broadcast)")
            else:
                # Inform sender that user is offline/not found
                self.send_to_user(username, {
                    'type': 'system',
                    'message': f"User '{to_user}' is not online",
                    'level': 'warning'
                })
                print(f"[PM] failed: {to_user} not online")
            # Echo to sender for local log (still send directly, harmless with broadcast above)
            self.send_to_user(username, {
                'type': 'private_chat',
                'from': username,
                'to': canonical_to or to_user,
                'message': text,
                'timestamp': datetime.now().strftime('%H:%M:%S')
            })
        
        elif msg_type == 'file_upload':
            # Handle file upload
            file_id = msg['file_id']
            with self.files_lock:
                self.shared_files[file_id] = {
                    'filename': msg['filename'],
                    'size': msg['size'],
                    'data': msg['data'],
                    'uploader': username,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            
            # Notify all clients
            self.broadcast_message({
                'type': 'file_available',
                'file_id': file_id,
                'filename': msg['filename'],
                'size': msg['size'],
                'uploader': username
            })
            print(f"[FILE] {username} uploaded {msg['filename']} ({msg['size']} bytes)")
        
        elif msg_type == 'file_download':
            # Handle file download request
            file_id = msg['file_id']
            with self.files_lock:
                if file_id in self.shared_files:
                    file_info = self.shared_files[file_id]
                    self.send_to_user(username, {
                        'type': 'file_data',
                        'file_id': file_id,
                        'filename': file_info['filename'],
                        'size': file_info['size'],
                        'data': file_info['data']
                    })
                    print(f"[FILE] Sent {file_info['filename']} to {username}")
    
    def handle_video_stream(self):
        """Handle incoming video UDP packets and broadcast to all clients"""
        while self.running:
            try:
                data, addr = self.video_socket.recvfrom(65535)
                
                # Parse username from packet header
                if len(data) < 4:
                    continue
                
                username_len = struct.unpack('I', data[:4])[0]
                if len(data) < 4 + username_len:
                    continue
                
                username = data[4:4+username_len].decode('utf-8')
                frame_data = data[4+username_len:]
                
                # Broadcast to all other clients
                with self.clients_lock:
                    for client_name, client_info in self.clients.items():
                        if client_name != username and client_info['video_addr']:
                            try:
                                self.video_socket.sendto(data, client_info['video_addr'])
                            except Exception as e:
                                print(f"[VIDEO] Error sending to {client_name}: {e}")
            
            except Exception as e:
                if self.running:
                    print(f"[VIDEO] Error: {e}")
    
    def handle_audio_stream(self):
        """Handle incoming audio UDP packets and broadcast to all clients"""
        while self.running:
            try:
                data, addr = self.audio_socket.recvfrom(65535)
                
                # Parse username from packet header
                if len(data) < 4:
                    continue
                
                username_len = struct.unpack('I', data[:4])[0]
                if len(data) < 4 + username_len:
                    continue
                
                username = data[4:4+username_len].decode('utf-8')
                audio_data = data[4+username_len:]
                
                # Broadcast to all other clients
                with self.clients_lock:
                    for client_name, client_info in self.clients.items():
                        if client_name != username and client_info['audio_addr']:
                            try:
                                self.audio_socket.sendto(data, client_info['audio_addr'])
                            except Exception as e:
                                print(f"[AUDIO] Error sending to {client_name}: {e}")
            
            except Exception as e:
                if self.running:
                    print(f"[AUDIO] Error: {e}")
    
    def send_message(self, sock, message):
        """Send JSON message over TCP with length prefix"""
        try:
            data = json.dumps(message).encode('utf-8')
            length = struct.pack('I', len(data))
            sock.sendall(length + data)
            return True
        except Exception as e:
            print(f"[TCP] Error sending message: {e}")
            return False
    
    def recv_message(self, sock):
        """Receive JSON message over TCP with length prefix"""
        try:
            # Receive length
            length_data = self.recv_exact(sock, 4)
            if not length_data:
                return None
            
            length = struct.unpack('I', length_data)[0]
            
            # Receive message
            data = self.recv_exact(sock, length)
            if not data:
                return None
            
            return json.loads(data.decode('utf-8'))
        except Exception as e:
            return None
    
    def recv_exact(self, sock, n):
        """Receive exactly n bytes from socket"""
        data = b''
        while len(data) < n:
            packet = sock.recv(n - len(data))
            if not packet:
                return None
            data += packet
        return data
    
    def broadcast_message(self, message, exclude=None):
        """Broadcast message to all clients except excluded one"""
        with self.clients_lock:
            for username, client_info in self.clients.items():
                if username != exclude:
                    self.send_message(client_info['tcp_socket'], message)
    
    def send_to_user(self, username, message):
        """Send message to specific user"""
        with self.clients_lock:
            if username in self.clients:
                self.send_message(self.clients[username]['tcp_socket'], message)
    
    def stop(self):
        """Stop the server"""
        print("[SERVER] Shutting down...")
        self.running = False
        
        # Close all sockets
        if self.tcp_socket:
            self.tcp_socket.close()
        if self.video_socket:
            self.video_socket.close()
        if self.audio_socket:
            self.audio_socket.close()
        
        print("[SERVER] Shutdown complete")

def main():
    server = LANCommServer()
    server.start()
    
    print("\n[SERVER] Press Ctrl+C to stop the server\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[SERVER] Received shutdown signal")
        server.stop()

if __name__ == '__main__':
    main()
