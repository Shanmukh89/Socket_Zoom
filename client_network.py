"""
Client networking module for LAN Communication
Handles TCP and UDP socket communication
"""

import socket
import threading
import json
import struct
import time

class ClientNetwork:
    def __init__(self, callback_handler):
        self.callback = callback_handler
        self.server_host = None
        self.tcp_port = 5555
        self.video_port = 5556
        self.audio_port = 5557
        
        self.username = None
        self.tcp_socket = None
        self.video_socket = None
        self.audio_socket = None
        
        self.connected = False
        self.running = False
    
    def connect(self, server_host, username):
        """Connect to server"""
        self.server_host = server_host
        self.username = username
        
        try:
            # TCP connection
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.connect((self.server_host, self.tcp_port))
            
            # UDP sockets
            self.video_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.video_socket.bind(('', 0))
            
            self.audio_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.audio_socket.bind(('', 0))
            
            # Register
            self.send_tcp_message({
                'type': 'register',
                'username': self.username
            })
            
            # Start receiver
            self.running = True
            threading.Thread(target=self._receive_tcp_loop, daemon=True).start()
            
            # Register UDP addresses with actual client IP (not 0.0.0.0)
            # Get the local IP that's connected to the server
            local_ip = self.tcp_socket.getsockname()[0]
            video_port = self.video_socket.getsockname()[1]
            audio_port = self.audio_socket.getsockname()[1]
            
            self.send_tcp_message({
                'type': 'video_register',
                'address': (local_ip, video_port)
            })
            self.send_tcp_message({
                'type': 'audio_register',
                'address': (local_ip, audio_port)
            })
            
            self.connected = True
            return True
        except Exception as e:
            return False, str(e)
    
    def send_tcp_message(self, message):
        """Send JSON message over TCP"""
        try:
            data = json.dumps(message).encode('utf-8')
            length = struct.pack('I', len(data))
            self.tcp_socket.sendall(length + data)
            return True
        except:
            return False
    
    def _recv_exact(self, sock, n):
        """Receive exactly n bytes"""
        data = b''
        while len(data) < n:
            packet = sock.recv(n - len(data))
            if not packet:
                return None
            data += packet
        return data
    
    def _receive_tcp_loop(self):
        """Receive TCP messages loop"""
        while self.running:
            try:
                # Receive length
                length_data = self._recv_exact(self.tcp_socket, 4)
                if not length_data:
                    break
                
                length = struct.unpack('I', length_data)[0]
                data = self._recv_exact(self.tcp_socket, length)
                if not data:
                    break
                
                msg = json.loads(data.decode('utf-8'))
                self.callback.on_server_message(msg)
            except:
                if self.running:
                    break
        
        if self.running:
            self.callback.on_disconnected()
    
    def send_video_packet(self, frame_data):
        """Send video packet"""
        try:
            username_bytes = self.username.encode('utf-8')
            header = struct.pack('I', len(username_bytes))
            packet = header + username_bytes + frame_data
            self.video_socket.sendto(packet, (self.server_host, self.video_port))
        except:
            pass
    
    def send_audio_packet(self, audio_data):
        """Send audio packet"""
        try:
            username_bytes = self.username.encode('utf-8')
            header = struct.pack('I', len(username_bytes))
            packet = header + username_bytes + audio_data
            self.audio_socket.sendto(packet, (self.server_host, self.audio_port))
        except:
            pass
    
    def receive_video_packet(self, timeout=0.01):
        """Receive video packet"""
        try:
            self.video_socket.settimeout(timeout)
            data, _ = self.video_socket.recvfrom(65535)
            
            if len(data) < 4:
                return None, None
            
            username_len = struct.unpack('I', data[:4])[0]
            if len(data) < 4 + username_len:
                return None, None
            
            username = data[4:4+username_len].decode('utf-8')
            frame_data = data[4+username_len:]
            
            return username, frame_data
        except socket.timeout:
            return None, None
        except:
            return None, None
    
    def receive_audio_packet(self, timeout=0.01):
        """Receive audio packet"""
        try:
            self.audio_socket.settimeout(timeout)
            data, _ = self.audio_socket.recvfrom(65535)
            
            if len(data) < 4:
                return None, None
            
            username_len = struct.unpack('I', data[:4])[0]
            if len(data) < 4 + username_len:
                return None, None
            
            username = data[4:4+username_len].decode('utf-8')
            audio_data = data[4+username_len:]
            
            return username, audio_data
        except socket.timeout:
            return None, None
        except:
            return None, None
    
    def disconnect(self):
        """Disconnect from server"""
        self.running = False
        self.connected = False
        
        if self.tcp_socket:
            try:
                self.tcp_socket.close()
            except:
                pass
        
        if self.video_socket:
            try:
                self.video_socket.close()
            except:
                pass
        
        if self.audio_socket:
            try:
                self.audio_socket.close()
            except:
                pass
