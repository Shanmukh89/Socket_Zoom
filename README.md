# LAN Communication System

A comprehensive multi-user communication application for Local Area Networks (LAN) with video conferencing, audio conferencing, screen sharing, group chat, and file transfer capabilities.

## Features

### ✨ Core Functionalities

1. **Multi-User Video Conferencing**
   - Real-time webcam video streaming
   - UDP-based for low latency
   - Automatic grid layout for multiple participants
   - 30 FPS video capture and display

2. **Multi-User Audio Conferencing**
   - Real-time audio capture and playback
   - UDP-based audio streaming
   - Low-latency audio communication
   - Automatic audio mixing

3. **Screen Sharing / Presentation**
   - One presenter at a time
   - Full screen capture and streaming
   - TCP-based for reliable delivery
   - Compressed JPEG transmission

4. **Group Text Chat**
   - Real-time text messaging
   - Message history with timestamps
   - System notifications for user events
   - Formatted chat display

5. **File Sharing**
   - Upload files to share with all participants
   - Download shared files
   - File metadata display (name, size, uploader)
   - Progress indication

## Architecture

### Client-Server Model
- **Server**: Central hub managing all connections and data relay
- **Client**: GUI application for end users
- **TCP**: Reliable communication for chat, file transfer, and control messages
- **UDP**: Low-latency streaming for video and audio

### Components

#### Server (`server.py`)
- Handles multiple simultaneous client connections
- Manages TCP control channel (port 5555)
- Relays UDP video streams (port 5556)
- Relays UDP audio streams (port 5557)
- Broadcasts messages to all connected clients
- Manages presentation control and file storage

#### Client Application
- `client.py` - Main entry point
- `client_gui.py` - Graphical user interface
- `client_network.py` - Network communication layer
- `client_media.py` - Media capture and streaming

## Installation

### Prerequisites
- Python 3.7 or higher
- Webcam (for video conferencing)
- Microphone (for audio conferencing)

### System Dependencies

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install python3-pip python3-tk portaudio19-dev
```

#### Linux (Fedora/RHEL)
```bash
sudo dnf install python3-pip python3-tkinter portaudio-devel
```

#### Windows
- Install Python 3.7+ from python.org (includes tkinter)
- PyAudio will be installed via pip

### Python Dependencies

Install required Python packages:
```bash
pip install -r requirements.txt
```

Or manually:
```bash
pip install opencv-python numpy Pillow pyaudio
```

## Usage

### Starting the Server

1. Open a terminal/command prompt
2. Navigate to the project directory
3. Run the server:
```bash
python server.py
```

The server will start and listen on:
- TCP Port 5555 (control, chat, files)
- UDP Port 5556 (video)
- UDP Port 5557 (audio)

**Server Output:**
```
[SERVER] Initializing LAN Communication Server
[SERVER] TCP Port: 5555, Video Port: 5556, Audio Port: 5557
[TCP] Server listening on 0.0.0.0:5555
[VIDEO] UDP server listening on 0.0.0.0:5556
[AUDIO] UDP server listening on 0.0.0.0:5557
[SERVER] All services started successfully
[SERVER] Press Ctrl+C to stop the server
```

### Starting the Client

1. Open a terminal/command prompt
2. Navigate to the project directory
3. Run the client:
```bash
python client.py
```

4. In the connection window:
   - Enter the **Server IP address** (use server's LAN IP)
   - Enter your **Username**
   - Click **Connect**

### Finding Server IP Address

#### Linux
```bash
ip addr show
# or
ifconfig
```
Look for inet address (e.g., 192.168.1.100)

#### Windows
```bash
ipconfig
```
Look for IPv4 Address

### Using the Application

#### Video Conferencing
1. Click **"Start Video"** to begin streaming your webcam
2. Your video will appear in the grid along with other participants
3. Click **"Stop Video"** to end streaming

#### Audio Conferencing
1. Click **"Start Audio"** to enable microphone and speakers
2. Speak into your microphone to communicate
3. Click **"Stop Audio"** to mute

#### Screen Sharing
1. Click **"Start Presenting"** to share your screen
2. Your screen will be visible to all participants
3. Only one person can present at a time
4. Click **"Stop Presenting"** to end sharing

#### Group Chat
1. Type your message in the text box at the bottom
2. Press **Enter** or click **"Send"**
3. Messages appear with timestamps and usernames

#### File Sharing
1. Click **"Upload File"** to share a file
2. Select the file from your system
3. All participants will see the file in their list
4. Others can select and click **"Download"** to save it

## Network Configuration

### Firewall Settings

Ensure the following ports are open on the server machine:
- TCP: 5555
- UDP: 5556
- UDP: 5557

#### Linux (UFW)
```bash
sudo ufw allow 5555/tcp
sudo ufw allow 5556/udp
sudo ufw allow 5557/udp
```

#### Linux (firewalld)
```bash
sudo firewall-cmd --add-port=5555/tcp --permanent
sudo firewall-cmd --add-port=5556/udp --permanent
sudo firewall-cmd --add-port=5557/udp --permanent
sudo firewall-cmd --reload
```

#### Windows Firewall
1. Open Windows Defender Firewall
2. Click "Advanced settings"
3. Create new Inbound Rules for ports 5555, 5556, 5557

### LAN Requirements

- All clients and server must be on the same local network
- No internet connection required
- Recommended: Gigabit Ethernet for best performance
- WiFi networks supported but may have higher latency

## Performance Optimization

### Recommended Hardware
- **CPU**: Quad-core processor or better
- **RAM**: 4GB minimum, 8GB recommended
- **Network**: Gigabit Ethernet
- **Webcam**: 720p or higher
- **Microphone**: Any USB or built-in microphone

### Quality Settings

Video quality can be adjusted in `client_media.py`:
```python
# Video resolution (line ~62)
frame = cv2.resize(frame, (320, 240))  # Increase for better quality

# JPEG quality (line ~63)
cv2.IMWRITE_JPEG_QUALITY, 50  # Increase (max 100) for better quality
```

Audio quality in `client_media.py`:
```python
# Audio sample rate (line ~25)
self.audio_rate = 16000  # Increase to 44100 for higher quality
```

## Troubleshooting

### Connection Issues

**Problem**: Cannot connect to server
- Verify server is running
- Check server IP address is correct
- Ensure firewall ports are open
- Confirm both machines are on same network

**Problem**: High latency or lag
- Check network speed and stability
- Reduce video quality settings
- Close other network-intensive applications
- Use wired Ethernet instead of WiFi

### Video Issues

**Problem**: Camera not detected
```bash
# Linux: Check camera access
ls /dev/video*

# Add user to video group if needed
sudo usermod -a -G video $USER
```

**Problem**: Video not displaying
- Ensure video streaming is started
- Check OpenCV installation
- Verify webcam permissions

### Audio Issues

**Problem**: PyAudio installation fails

**Linux**:
```bash
sudo apt-get install portaudio19-dev python3-pyaudio
pip install pyaudio
```

**Windows**:
```bash
# Use precompiled wheel
pip install pipwin
pipwin install pyaudio
```

**Problem**: No audio output
- Check system audio settings
- Verify microphone/speaker permissions
- Test with other audio applications

### Screen Sharing Issues

**Problem**: Screen capture not working
- Ensure PIL/Pillow is installed correctly
- Check screen capture permissions (macOS/Linux)
- Try running with elevated privileges if needed

## Technical Specifications

### Network Protocols

| Feature | Protocol | Port | Packet Size |
|---------|----------|------|-------------|
| Control | TCP | 5555 | Variable |
| Chat | TCP | 5555 | < 64KB |
| File Transfer | TCP | 5555 | Variable |
| Screen Sharing | TCP | 5555 | ~50-200KB |
| Video Streaming | UDP | 5556 | ~10-30KB |
| Audio Streaming | UDP | 5557 | ~2KB |

### Codec Information

- **Video**: JPEG compression (adjustable quality)
- **Audio**: Raw PCM 16-bit
- **Screen**: JPEG compression
- **Files**: Base64 encoding over TCP

### Performance Metrics

- **Video Latency**: <100ms on LAN
- **Audio Latency**: <50ms on LAN
- **Max Concurrent Users**: 10-20 (hardware dependent)
- **Video FPS**: 30 (configurable)
- **Screen Sharing FPS**: 10 (optimized for bandwidth)

## Security Considerations

### Current Implementation
- No encryption (data transmitted in plaintext)
- No authentication beyond username
- Suitable for trusted local networks only

### Recommendations for Production
- Implement TLS/SSL for TCP connections
- Add DTLS for UDP streams
- Implement user authentication
- Add access control lists
- Use VPN for extended network access

## Development

### Project Structure
```
lan-communication/
├── server.py              # Server application
├── client.py              # Client entry point
├── client_gui.py          # GUI implementation
├── client_network.py      # Network layer
├── client_media.py        # Media handling
├── requirements.txt       # Python dependencies
└── README.md             # Documentation
```

### Extending the Application

#### Adding New Features
1. Define message type in protocol
2. Add handler in server (`process_message`)
3. Add handler in client (`on_server_message`)
4. Update GUI as needed

#### Custom Protocol Messages
```python
# Example: Send custom message
self.network.send_tcp_message({
    'type': 'custom_message',
    'data': 'your_data'
})
```

## License

This project is provided as-is for educational and internal use purposes.

## Support

For issues or questions:
1. Check the Troubleshooting section
2. Review server and client console output
3. Verify network configuration
4. Test with minimal setup (server + 1 client)

## Acknowledgments

Built using:
- OpenCV for video processing
- PyAudio for audio handling
- Tkinter for GUI
- Python socket programming

---

**Version**: 1.0.0  
**Platform**: Cross-platform (Linux, Windows, macOS)  
**Python**: 3.7+
