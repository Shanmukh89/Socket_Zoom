"""
Client media module for video and audio handling
"""


import cv2
import pyaudio
import numpy as np
import threading
import time
from PIL import Image
import subprocess
import platform
import random
import string


class MediaHandler:
    def __init__(self, network, callback):
        self.network = network
        self.callback = callback
        
        # Video
        self.video_capture = None
        self.video_streaming = False
        self.video_thread = None
        
        # Audio
        self.audio = None
        self.audio_streaming = False
        self.audio_capture_thread = None
        self.audio_playback_thread = None
        self.audio_format = pyaudio.paInt16
        self.audio_channels = 1
        self.audio_rate = 16000
        self.audio_chunk = 1024
        
        # Screen sharing
        self.presenting = False
        self.present_thread = None
        
        # PipeWire/Portal session tracking
        self.portal_session_handle = None
        self.pipewire_node_id = None
        self.gst_pipeline = None
    
    # Video methods
    def start_video(self):
        """Start video capture and streaming"""
        try:
            self.video_capture = cv2.VideoCapture(0)
            if not self.video_capture.isOpened():
                return False, "Failed to open camera"
            
            self.video_streaming = True
            self.video_thread = threading.Thread(target=self._video_capture_loop, daemon=True)
            self.video_thread.start()
            return True, "Video started"
        except Exception as e:
            return False, str(e)
    
    def stop_video(self):
        """Stop video streaming"""
        self.video_streaming = False
        if self.video_capture:
            self.video_capture.release()
            self.video_capture = None
    
    def _video_capture_loop(self):
        """Video capture and send loop"""
        while self.video_streaming:
            try:
                ret, frame = self.video_capture.read()
                if not ret:
                    continue
                
                # Resize and compress
                frame = cv2.resize(frame, (320, 240))
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
                
                # Send packet
                self.network.send_video_packet(buffer.tobytes())
                
                # Also make available for local display
                self.callback.on_local_video_frame(frame)
                
                time.sleep(0.033)  # ~30 FPS
            except Exception as e:
                print(f"Video capture error: {e}")
                break
    
    def receive_video_frames(self):
        """Receive video frames from network"""
        frames = {}
        while True:
            username, frame_data = self.network.receive_video_packet(timeout=0.001)
            if username is None:
                break
            
            # Don't process own video frames (server shouldn't send them, but double-check)
            if username == self.network.username:
                continue
            
            try:
                nparr = np.frombuffer(frame_data, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is not None:
                    frames[username] = frame
            except:
                pass
        
        return frames
    
    # Audio methods
    def start_audio(self):
        """Start audio capture and playback"""
        try:
            self.audio = pyaudio.PyAudio()
            self.audio_streaming = True
            
            # Start capture thread
            self.audio_capture_thread = threading.Thread(
                target=self._audio_capture_loop, daemon=True)
            self.audio_capture_thread.start()
            
            # Start playback thread
            self.audio_playback_thread = threading.Thread(
                target=self._audio_playback_loop, daemon=True)
            self.audio_playback_thread.start()
            
            return True, "Audio started"
        except Exception as e:
            return False, str(e)
    
    def stop_audio(self):
        """Stop audio streaming"""
        self.audio_streaming = False
        
        # Wait for threads to finish (with timeout)
        if self.audio_capture_thread and self.audio_capture_thread.is_alive():
            self.audio_capture_thread.join(timeout=2.0)
        if self.audio_playback_thread and self.audio_playback_thread.is_alive():
            self.audio_playback_thread.join(timeout=2.0)
        
        # Now safe to terminate PyAudio
        if self.audio:
            try:
                self.audio.terminate()
            except Exception as e:
                print(f"Error terminating audio: {e}")
            self.audio = None
    
    def _audio_capture_loop(self):
        """Audio capture and send loop"""
        stream = None
        try:
            stream = self.audio.open(
                format=self.audio_format,
                channels=self.audio_channels,
                rate=self.audio_rate,
                input=True,
                frames_per_buffer=self.audio_chunk
            )
            
            while self.audio_streaming:
                try:
                    data = stream.read(self.audio_chunk, exception_on_overflow=False)
                    self.network.send_audio_packet(data)
                except Exception as e:
                    if self.audio_streaming:  # Only log if not intentionally stopped
                        print(f"Audio send error: {e}")
                    break
        except Exception as e:
            print(f"Audio capture error: {e}")
        finally:
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except:
                    pass
    
    def _audio_playback_loop(self):
        """Audio receive and playback loop"""
        stream = None
        try:
            stream = self.audio.open(
                format=self.audio_format,
                channels=self.audio_channels,
                rate=self.audio_rate,
                output=True,
                frames_per_buffer=self.audio_chunk
            )
            
            while self.audio_streaming:
                try:
                    username, audio_data = self.network.receive_audio_packet(timeout=0.1)
                    # IMPORTANT: Don't play back own audio to prevent echo
                    if audio_data and username != self.network.username:
                        stream.write(audio_data)
                except Exception as e:
                    if self.audio_streaming:  # Only log if not intentionally stopped
                        print(f"Audio playback error: {e}")
                    break
        except Exception as e:
            print(f"Audio playback loop error: {e}")
        finally:
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except:
                    pass
    
    # Screen sharing methods - xdg-desktop-portal + PipeWire
    def start_presentation(self):
        """Start screen sharing using xdg-desktop-portal + PipeWire"""
        print("[PORTAL] Starting screen presentation via xdg-desktop-portal...")
        
        self.presenting = True
        self.present_thread = threading.Thread(target=self._presentation_loop, daemon=True)
        self.present_thread.start()
        print("[PORTAL] Screen presentation thread started")
    
    def stop_presentation(self):
        """Stop screen sharing and cleanup portal session"""
        print("[PORTAL] Stopping screen presentation...")
        self.presenting = False
        
        # Cleanup GStreamer pipeline
        if self.gst_pipeline:
            try:
                self.gst_pipeline.set_state(Gst.State.NULL)
                print("[PORTAL] GStreamer pipeline stopped")
            except Exception as e:
                print(f"[PORTAL] Error stopping pipeline: {e}")
            self.gst_pipeline = None
        
        # Close portal session
        if self.portal_session_handle:
            try:
                import dbus
                bus = dbus.SessionBus()
                portal = bus.get_object('org.freedesktop.portal.Desktop',
                                       '/org/freedesktop/portal/desktop')
                portal_iface = dbus.Interface(portal, 'org.freedesktop.portal.ScreenCast')
                # Close session
                session_obj = bus.get_object('org.freedesktop.portal.Desktop',
                                            self.portal_session_handle)
                session_iface = dbus.Interface(session_obj, 'org.freedesktop.portal.Session')
                session_iface.Close()
                print("[PORTAL] Portal session closed")
            except Exception as e:
                print(f"[PORTAL] Error closing portal session: {e}")
            self.portal_session_handle = None
        
        self.pipewire_node_id = None
        print("[PORTAL] Screen presentation stopped")
    
    def _request_screencast_session(self):
        """Request a screencast session via xdg-desktop-portal D-Bus"""
        try:
            import dbus
            from dbus.mainloop.glib import DBusGMainLoop
            
            DBusGMainLoop(set_as_default=True)
            
            bus = dbus.SessionBus()
            portal = bus.get_object('org.freedesktop.portal.Desktop',
                                   '/org/freedesktop/portal/desktop')
            screencast_iface = dbus.Interface(portal, 'org.freedesktop.portal.ScreenCast')
            
            # Generate unique session token
            session_token = 'screenshare_' + ''.join(random.choices(string.ascii_letters + string.digits, k=16))
            sender_name = bus.get_unique_name()[1:].replace('.', '_')
            session_handle = f'/org/freedesktop/portal/desktop/session/{sender_name}/{session_token}'
            
            print(f"[PORTAL] Creating session with token: {session_token}")
            
            # Create session
            options = {
                'session_handle_token': session_token,
                'handle_token': 'request_' + ''.join(random.choices(string.ascii_letters + string.digits, k=16))
            }
            
            response = screencast_iface.CreateSession(options)
            print(f"[PORTAL] CreateSession response: {response}")
            
            return session_handle
            
        except Exception as e:
            print(f"[PORTAL] ERROR: Failed to create session: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _start_screencast_portal(self, session_handle):
        """Start the screencast and get PipeWire stream ID"""
        try:
            import dbus
            from dbus.mainloop.glib import DBusGMainLoop
            from gi.repository import GLib
            
            # Initialize DBus GLib main loop
            DBusGMainLoop(set_as_default=True)
            
            bus = dbus.SessionBus()
            portal = bus.get_object('org.freedesktop.portal.Desktop',
                                   '/org/freedesktop/portal/desktop')
            screencast_iface = dbus.Interface(portal, 'org.freedesktop.portal.ScreenCast')
            
            # Create a GLib main loop for this thread
            main_loop = GLib.MainLoop()
            pipewire_node_id = [None]
            error_occurred = [False]
            
            # Step 1: Select sources (monitor/window)
            print("[PORTAL] Selecting sources...")
            select_options = {
                'types': dbus.UInt32(1 | 2),  # Monitor (1) and Window (2)
                'multiple': dbus.Boolean(False),
                'handle_token': 'select_' + ''.join(random.choices(string.ascii_letters + string.digits, k=16))
            }
            
            select_request_path = screencast_iface.SelectSources(session_handle, select_options)
            print(f"[PORTAL] SelectSources request path: {select_request_path}")
            
            def on_select_response(response_code, results):
                print(f"[PORTAL] SelectSources response: code={response_code}")
                if response_code == 0:
                    print("[PORTAL] Sources selected successfully")
                    # Now call Start
                    try:
                        print("[PORTAL] Starting screencast (user permission dialog will appear)...")
                        start_options = {
                            'handle_token': 'start_' + ''.join(random.choices(string.ascii_letters + string.digits, k=16))
                        }
                        
                        start_request_path = screencast_iface.Start(session_handle, '', start_options)
                        print(f"[PORTAL] Start request path: {start_request_path}")
                        
                        # Connect to Start response
                        start_request_obj = bus.get_object('org.freedesktop.portal.Desktop', start_request_path)
                        start_request_iface = dbus.Interface(start_request_obj, 'org.freedesktop.portal.Request')
                        start_request_iface.connect_to_signal('Response', on_start_response)
                        
                    except Exception as e:
                        print(f"[PORTAL] ERROR in Start: {e}")
                        error_occurred[0] = True
                        main_loop.quit()
                else:
                    print(f"[PORTAL] SelectSources failed with code {response_code}")
                    error_occurred[0] = True
                    main_loop.quit()
            
            def on_start_response(response_code, results):
                print(f"[PORTAL] Start response: code={response_code}, results={results}")
                if response_code == 0:  # Success
                    streams = results.get('streams', [])
                    if streams:
                        pipewire_node_id[0] = streams[0][0]  # First stream's node ID
                        print(f"[PORTAL] Got PipeWire node ID: {pipewire_node_id[0]}")
                    else:
                        print("[PORTAL] ERROR: No streams in response")
                        error_occurred[0] = True
                else:
                    print(f"[PORTAL] User denied permission or error occurred (code={response_code})")
                    error_occurred[0] = True
                main_loop.quit()
            
            # Connect to SelectSources response
            select_request_obj = bus.get_object('org.freedesktop.portal.Desktop', select_request_path)
            select_request_iface = dbus.Interface(select_request_obj, 'org.freedesktop.portal.Request')
            select_request_iface.connect_to_signal('Response', on_select_response)
            
            # Set timeout
            def on_timeout():
                print("[PORTAL] ERROR: Timeout waiting for portal response")
                error_occurred[0] = True
                main_loop.quit()
                return False  # Don't repeat
            
            GLib.timeout_add_seconds(30, on_timeout)
            
            # Run the main loop (this will block until quit() is called)
            print("[PORTAL] Waiting for user interaction with portal dialog...")
            main_loop.run()
            
            if error_occurred[0] or pipewire_node_id[0] is None:
                return None
            
            return pipewire_node_id[0]
            
        except Exception as e:
            print(f"[PORTAL] ERROR: Failed to start screencast: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _presentation_loop(self):
        """Screen capture and send loop using xdg-desktop-portal + PipeWire + GStreamer on Linux, or mss on Windows"""
        import platform
        if platform.system() == 'Windows':
            import mss
            import base64
            import uuid
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                frame_idx = 0
                while self.presenting:
                    sct_img = sct.grab(monitor)
                    img = np.array(sct_img)
                    img = img[..., :3]  # BGRA to BGR
                    # Resize to max 960x540 while keeping aspect ratio
                    h, w, _ = img.shape
                    max_w, max_h = 960, 540
                    scale = min(max_w/w, max_h/h, 1.0)
                    if scale < 1.0:
                        img = cv2.resize(img, (int(w*scale), int(h*scale)))
                    # Use PNG for lossless, robust transfer
                    _, buffer = cv2.imencode('.png', img)
                    frame_data = base64.b64encode(buffer).decode('utf-8')
                    print(f"[MSS] Screen: orig=({w},{h}), scaled={img.shape}, buffer={len(buffer)}, base64={len(frame_data)}")
                    self.network.send_tcp_message({
                        'type': 'screen_frame',
                        'frame_data': frame_data,
                        'frame_id': str(uuid.uuid4()),
                    })
                    frame_idx += 1
                    self.callback.on_local_screen_frame(Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)))
                    time.sleep(0.25)  # 4 FPS
            return
        # Original Linux/gi path below
        try:
            import gi
            gi.require_version('Gst', '1.0')
            from gi.repository import Gst, GLib
            import dbus
        except ImportError as e:
            print(f"[PORTAL] ERROR: Required libraries not available: {e}")
            print("[PORTAL] Please run: ./install_pipewire_deps.sh")
            self.presenting = False
            return
        
        # Initialize GStreamer
        Gst.init(None)
        print("[PORTAL] GStreamer initialized")
        
        # Step 1: Request screencast session
        session_handle = self._request_screencast_session()
        if not session_handle:
            print("[PORTAL] Failed to create session")
            self.presenting = False
            return
        
        self.portal_session_handle = session_handle
        
        # Step 2: Start screencast and get PipeWire node ID
        pipewire_node_id = self._start_screencast_portal(session_handle)
        if not pipewire_node_id:
            print("[PORTAL] Failed to get PipeWire node ID")
            self.presenting = False
            return
        
        self.pipewire_node_id = pipewire_node_id
        print(f"[PORTAL] Successfully obtained PipeWire node ID: {pipewire_node_id}")
        
        # Step 3: Build GStreamer pipeline
        # Pipeline: pipewiresrc -> videoconvert -> videoscale -> jpegenc -> appsink
        pipeline_str = (
            f'pipewiresrc path={pipewire_node_id} do-timestamp=true ! '
            'video/x-raw ! '
            'videoconvert ! '
            'videoscale ! '
            'video/x-raw,width=1280,height=720 ! '
            'jpegenc quality=75 ! '
            'appsink name=sink emit-signals=true sync=false max-buffers=1 drop=true'
        )
        
        print(f"[PORTAL] Creating GStreamer pipeline: {pipeline_str}")
        
        try:
            pipeline = Gst.parse_launch(pipeline_str)
            self.gst_pipeline = pipeline
            
            # Get appsink element
            appsink = pipeline.get_by_name('sink')
            if not appsink:
                print("[PORTAL] ERROR: Could not get appsink element")
                self.presenting = False
                return
            
            # Frame counter
            frame_count = [0]
            
            # Callback for new samples
            def on_new_sample(sink):
                if not self.presenting:
                    return Gst.FlowReturn.EOS
                
                try:
                    sample = sink.emit('pull-sample')
                    if sample:
                        buffer = sample.get_buffer()
                        success, map_info = buffer.map(Gst.MapFlags.READ)
                        
                        if success:
                            # Get JPEG data directly from buffer
                            jpeg_data = bytes(map_info.data)
                            buffer.unmap(map_info)
                            
                            # Encode to base64 and send via TCP (same as old ffmpeg method)
                            import base64
                            frame_data = base64.b64encode(jpeg_data).decode('utf-8')
                            
                            # Send via TCP message (for screen sharing)
                            self.network.send_tcp_message({
                                'type': 'screen_frame',
                                'frame_data': frame_data
                            })
                            
                            frame_count[0] += 1
                            if frame_count[0] % 30 == 0:  # Log every 3 seconds at 10 FPS
                                print(f"[PORTAL] Streaming: {frame_count[0]} frames sent ({len(jpeg_data)} bytes/frame)")
                    
                    return Gst.FlowReturn.OK
                    
                except Exception as e:
                    print(f"[PORTAL] Frame processing error: {e}")
                    return Gst.FlowReturn.ERROR
            
            # Connect callback
            appsink.connect('new-sample', on_new_sample)
            
            # Start pipeline
            print("[PORTAL] Starting GStreamer pipeline...")
            ret = pipeline.set_state(Gst.State.PLAYING)
            if ret == Gst.StateChangeReturn.FAILURE:
                print("[PORTAL] ERROR: Unable to set pipeline to PLAYING state")
                self.presenting = False
                return
            
            print("[PORTAL] Pipeline started successfully - screen sharing active!")
            
            # Keep pipeline running while presenting
            bus = pipeline.get_bus()
            while self.presenting:
                msg = bus.timed_pop_filtered(
                    100 * Gst.MSECOND,
                    Gst.MessageType.ERROR | Gst.MessageType.EOS | Gst.MessageType.STATE_CHANGED
                )
                
                if msg:
                    if msg.type == Gst.MessageType.ERROR:
                        err, debug = msg.parse_error()
                        print(f"[PORTAL] Pipeline error: {err.message}")
                        print(f"[PORTAL] Debug info: {debug}")
                        break
                    elif msg.type == Gst.MessageType.EOS:
                        print("[PORTAL] End of stream")
                        break
                
                time.sleep(0.01)
            
            print(f"[PORTAL] Stopping pipeline (sent {frame_count[0]} frames total)")
            
        except Exception as e:
            print(f"[PORTAL] Pipeline error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Cleanup is handled in stop_presentation()
            pass