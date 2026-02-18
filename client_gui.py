"""
LAN Communication Client GUI
Main graphical interface for the application
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import cv2
import numpy as np
from PIL import Image, ImageTk
from datetime import datetime
import base64
import os

from client_network import ClientNetwork
from client_media import MediaHandler

class LANCommClientGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("LAN Communication Client")
        self.root.geometry("1400x900")
        # Zoom design: dark neutral background
        self.root.configure(bg='#1C1C1C')
        
        # Brand colors used by buttons (must be defined before building UI)
        self._brand_blue = '#2D8CFF'
        self._brand_blue_hover = '#0E71EB'
        self._danger_red = '#E74C3C'
        self._danger_red_hover = '#C0392B'
        
        # Network and media
        self.network = ClientNetwork(self)
        self.media = None
        
        # State
        self.username = None
        self.received_videos = {}
        self.video_lock = threading.Lock()
        self.local_video_frame = None
        self.screen_frame = None
        self.last_screen_frame = None  # Track last displayed frame to avoid redundant updates
        self.presenter_name = None
        self.available_files = {}
        
        # Setup GUI
        self.setup_styles()
        self.create_connection_screen()
        self.create_main_interface()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _apply_hover(self, widget, normal_bg, hover_bg):
        widget.configure(activebackground=hover_bg)
        widget.bind('<Enter>', lambda e: widget.configure(bg=hover_bg))
        widget.bind('<Leave>', lambda e: widget.configure(bg=normal_bg))

    def _style_primary(self, button):
        button.configure(relief='flat', bd=0, bg=self._brand_blue, fg='#FFFFFF',
                         activeforeground='#FFFFFF', cursor='hand2')
        self._apply_hover(button, self._brand_blue, self._brand_blue_hover)

    def _style_danger(self, button):
        button.configure(relief='flat', bd=0, bg=self._danger_red, fg='#FFFFFF',
                         activeforeground='#FFFFFF', cursor='hand2')
        self._apply_hover(button, self._danger_red, self._danger_red_hover)
    
    def _style_disabled(self, button):
        """Greyed-out button style with no hover effect."""
        disabled_bg = '#3C3C3C'
        disabled_fg = '#9E9E9E'
        button.configure(relief='flat', bd=0, bg=disabled_bg, fg=disabled_fg,
                         activeforeground=disabled_fg, activebackground=disabled_bg,
                         cursor='arrow')
        # Override hover to keep same background (remove hover effect)
        button.bind('<Enter>', lambda e, b=button, c=disabled_bg: b.configure(bg=c))
        button.bind('<Leave>', lambda e, b=button, c=disabled_bg: b.configure(bg=c))

    def _create_rounded_panel(self, parent, radius=32, panel_bg='#232323'):
        """Create a simple rounded rectangle panel using a Canvas with an inner Frame.
        Returns (wrapper, content_frame).
        """
        wrapper = tk.Frame(parent, bg=parent.cget('bg'))
        canvas = tk.Canvas(wrapper, bg=parent.cget('bg'), highlightthickness=0, bd=0)
        canvas.pack()
        content = tk.Frame(canvas, bg=panel_bg)
        # place content with padding equal to radius so arcs have room
        canvas.create_window(radius, radius, anchor='nw', window=content)

        def redraw(event=None):
            req_w = content.winfo_reqwidth() + (radius * 2)
            req_h = content.winfo_reqheight() + (radius * 2)
            canvas.config(width=req_w, height=req_h)
            w = max(2, req_w)
            h = max(2, req_h)
            r = max(2, radius)
            canvas.delete('bg')
            # corners
            canvas.create_arc(0, 0, 2*r, 2*r, start=90, extent=90, fill=panel_bg, outline=panel_bg, tags='bg')
            canvas.create_arc(w-2*r, 0, w, 2*r, start=0, extent=90, fill=panel_bg, outline=panel_bg, tags='bg')
            canvas.create_arc(0, h-2*r, 2*r, h, start=180, extent=90, fill=panel_bg, outline=panel_bg, tags='bg')
            canvas.create_arc(w-2*r, h-2*r, w, h, start=270, extent=90, fill=panel_bg, outline=panel_bg, tags='bg')
            # edges
            canvas.create_rectangle(r, 0, w-r, h, fill=panel_bg, outline=panel_bg, tags='bg')
            canvas.create_rectangle(0, r, w, h-r, fill=panel_bg, outline=panel_bg, tags='bg')

        content.bind('<Configure>', redraw)
        wrapper.after(0, redraw)
        return wrapper, content

    def _create_pill_button(self, parent, text, command, radius=22,
                             bg_color=None, hover_color=None, fg_color='#FFFFFF',
                             padx=28, pady=12, font=('Segoe UI', 14, 'bold')):
        """Canvas-based rounded button. Returns the container frame."""
        bg_color = bg_color or self._brand_blue
        hover_color = hover_color or self._brand_blue_hover
        container = tk.Frame(parent, bg=parent.cget('bg'))
        c = tk.Canvas(container, bg=parent.cget('bg'), highlightthickness=0, bd=0, cursor='hand2')
        c.pack()
        # Measure text
        tmp = tk.Label(container, text=text, font=font)
        tmp.update_idletasks()
        tw, th = tmp.winfo_reqwidth(), tmp.winfo_reqheight()
        tmp.destroy()
        w = tw + padx*2
        h = th + pady*2
        c.config(width=w, height=h)

        def draw(color):
            c.delete('btn')
            r = radius
            # rounded rect
            c.create_arc(0, 0, 2*r, 2*r, start=90, extent=90, fill=color, outline=color, tags='btn')
            c.create_arc(w-2*r, 0, w, 2*r, start=0, extent=90, fill=color, outline=color, tags='btn')
            c.create_arc(0, h-2*r, 2*r, h, start=180, extent=90, fill=color, outline=color, tags='btn')
            c.create_arc(w-2*r, h-2*r, w, h, start=270, extent=90, fill=color, outline=color, tags='btn')
            c.create_rectangle(r, 0, w-r, h, fill=color, outline=color, tags='btn')
            c.create_rectangle(0, r, w, h-r, fill=color, outline=color, tags='btn')
            c.create_text(w//2, h//2, text=text, fill=fg_color, font=font, tags='btn')

        draw(bg_color)
        c.bind('<Enter>', lambda e: draw(hover_color))
        c.bind('<Leave>', lambda e: draw(bg_color))
        c.bind('<Button-1>', lambda e: command())
        return container

    def _init_login_background(self):
        """Set a full-window background image for the login screen and keep it scaled."""
        try:
            img_path = os.path.join(os.path.dirname(__file__), 'Spectral_20Dark_20-_2050.jpg')
            from PIL import Image
            self._bg_original = Image.open(img_path).convert('RGB')
        except Exception:
            self._bg_original = None
            return
        # Background label stretched to full window
        if getattr(self, '_bg_label', None) is None:
            self._bg_label = tk.Label(self.root, bd=0)
            self._bg_label.place(relx=0, rely=0, relwidth=1, relheight=1)
            self._bg_label.lower()  # behind everything

        def resize_bg(event=None):
            try:
                if self._bg_original is None:
                    return
                w = max(1, self.root.winfo_width())
                h = max(1, self.root.winfo_height())
                ow, oh = self._bg_original.size
                # cover behavior: scale by max ratio
                scale = max(w / ow, h / oh)
                nw, nh = max(1, int(ow * scale)), max(1, int(oh * scale))
                img = self._bg_original.resize((nw, nh), Image.LANCZOS)
                # center crop to window
                left = max(0, (nw - w) // 2)
                top = max(0, (nh - h) // 2)
                img = img.crop((left, top, left + w, top + h))
                from PIL import ImageTk
                self._bg_photo = ImageTk.PhotoImage(img)
                self._bg_label.configure(image=self._bg_photo)
            except Exception:
                pass

        # Bind and perform initial draw
        self._bg_bind_id = self.root.bind('<Configure>', lambda e: resize_bg())
        self.root.after(0, resize_bg)
    
    def setup_styles(self):
        """Configure ttk styles"""
        style = ttk.Style()
        style.theme_use('clam')
        # Base surfaces
        style.configure('TFrame', background='#1C1C1C')
        style.configure('TLabel', background='#1C1C1C', foreground='#FFFFFF')
    
    def create_connection_screen(self):
        """Create connection screen"""
        # Background image for login
        self._init_login_background()
        # Rounded panel centered
        self.connection_wrapper, self.connection_frame = self._create_rounded_panel(self.root, radius=32, panel_bg='#232323')
        self.connection_wrapper.place(relx=0.5, rely=0.5, anchor='center')
        
        tk.Label(self.connection_frame, text="LAN Communication",
                font=('Segoe UI', 22, 'bold'), bg='#232323', fg='#FFFFFF').pack(pady=24)
        
        tk.Label(self.connection_frame, text="Server IP:",
                bg='#232323', fg='#A1A1A1', font=('Segoe UI', 14)).pack(pady=8)
        self.server_entry = tk.Entry(self.connection_frame, font=('Segoe UI', 14), width=32,
                                     bg='#1C1C1C', fg='#FFFFFF', insertbackground='#FFFFFF', relief='solid', bd=1, highlightthickness=0)
        self.server_entry.pack(pady=8, ipady=6)
        self.server_entry.insert(0, "127.0.0.1")
        
        tk.Label(self.connection_frame, text="Username:",
                bg='#232323', fg='#A1A1A1', font=('Segoe UI', 14)).pack(pady=8)
        self.username_entry = tk.Entry(self.connection_frame, font=('Segoe UI', 14), width=32,
                                       bg='#1C1C1C', fg='#FFFFFF', insertbackground='#FFFFFF', relief='solid', bd=1, highlightthickness=0)
        self.username_entry.pack(pady=8, ipady=6)
        
        join_btn = self._create_pill_button(self.connection_frame, text='Join', command=self.connect_to_server,
                                            radius=22, bg_color=self._brand_blue, hover_color=self._brand_blue_hover)
        join_btn.pack(pady=24)
        
        self.status_label = tk.Label(self.connection_frame, text="",
                                     bg='#232323', fg='#E74C3C', font=('Segoe UI', 12))
        self.status_label.pack()
    
    def create_main_interface(self):
        """Create main application interface"""
        self.main_frame = tk.Frame(self.root, bg='#1C1C1C')
        
        # Top bar
        top_bar = tk.Frame(self.main_frame, bg='#232323', height=60)
        top_bar.pack(fill='x')
        
        tk.Label(top_bar, text="LAN Communication", font=('Segoe UI', 18, 'bold'),
                bg='#232323', fg='#FFFFFF').pack(side='left', padx=20, pady=12)
        
        self.username_label = tk.Label(top_bar, text="", font=('Segoe UI', 14),
                                       bg='#232323', fg='#2D8CFF')
        self.username_label.pack(side='right', padx=20)
        
        # Main content: Left 50% Video/Audio, Right 50% split vertically (Screen Share top, Group Chat bottom)
        content = tk.Frame(self.main_frame, bg='#1C1C1C')
        content.pack(fill='both', expand=True)

        # Two equal columns
        content.grid_rowconfigure(0, weight=1)
        # Enforce strict 50/50 split using uniform columns
        content.grid_columnconfigure(0, weight=1, uniform='cols')
        content.grid_columnconfigure(1, weight=1, uniform='cols')

        # Left: Video/Audio uses entire left half
        video_section = tk.Frame(content, bg='#232323')
        video_section.grid(row=0, column=0, sticky='nsew', padx=(16, 8), pady=16)
        self.create_video_panel(video_section)

        # Right: split into two equal halves (top: Screen Share, bottom: Group Chat)
        right_section = tk.Frame(content, bg='#1C1C1C')
        right_section.grid(row=0, column=1, sticky='nsew', padx=(8, 16), pady=16)
        # Top row (screen share) minsize is set dynamically to enforce square; chat fills the rest
        right_section.grid_rowconfigure(0, weight=0)
        right_section.grid_rowconfigure(1, weight=1)
        right_section.grid_columnconfigure(0, weight=1)

        # Bind to resize so we can keep screen share as a square
        self.right_section = right_section
        self.right_section.bind('<Configure>', self._on_right_section_resize)

        screen_section = tk.Frame(right_section, bg='#232323')
        screen_section.grid(row=0, column=0, sticky='nsew', pady=(0, 8))
        self.create_screen_panel(screen_section)

        chat_section = tk.Frame(right_section, bg='#232323')
        chat_section.grid(row=1, column=0, sticky='nsew', pady=(8, 0))
        self.create_chat_panel(chat_section)
    
    def create_video_panel(self, parent):
        """Create video conferencing panel"""
        header = tk.Frame(parent, bg='#232323')
        header.pack(fill='x', pady=8, padx=8)
        
        tk.Label(header, text="Video Conference", font=('Segoe UI', 14, 'bold'),
                bg='#232323', fg='#FFFFFF').pack(side='left', padx=12)
        
        self.video_btn = tk.Button(header, text="🎥 Start Video", bg=self._brand_blue,
                                   fg='#FFFFFF', command=self.toggle_video, padx=12, pady=6)
        self.video_btn.pack(side='right', padx=6)
        self._style_primary(self.video_btn)
        
        self.audio_btn = tk.Button(header, text="🎙 Start Audio", bg=self._brand_blue,
                                   fg='#FFFFFF', command=self.toggle_audio, padx=12, pady=6)
        self.audio_btn.pack(side='right', padx=6)
        self._style_primary(self.audio_btn)
        
        # Video canvas
        self.video_canvas = tk.Canvas(parent, bg='#1C1C1C', height=1,
                                     highlightthickness=0)
        self.video_canvas.pack(fill='both', expand=True, padx=8, pady=8)
    
    def create_screen_panel(self, parent):
        """Create screen sharing panel"""
        header = tk.Frame(parent, bg='#232323')
        header.pack(fill='x', pady=8, padx=8)
        
        tk.Label(header, text="Screen Sharing", font=('Segoe UI', 14, 'bold'),
                bg='#232323', fg='#FFFFFF').pack(side='left', padx=12)
        
        self.present_btn = tk.Button(header, text="🖥 Start Presenting", bg=self._brand_blue,
                                     fg='#FFFFFF', command=self.toggle_presentation, padx=12, pady=6)
        self.present_btn.pack(side='right', padx=6)
        self._style_primary(self.present_btn)
        
        self.screen_canvas = tk.Canvas(parent, bg='#1C1C1C', height=1,
                                      highlightthickness=0)
        self.screen_canvas.pack(fill='both', expand=True, padx=8, pady=8)
    
    def create_users_panel(self, parent):
        """Create users list panel"""
        frame = tk.LabelFrame(parent, text="Online Users", bg='#232323',
                             fg='#FFFFFF', font=('Segoe UI', 14, 'bold'), bd=0, labelanchor='nw')
        frame.pack(fill='x', pady=(8, 0), padx=8)
        
        self.users_listbox = tk.Listbox(frame, height=3, bg='#1C1C1C', fg='#FFFFFF',
                                        selectbackground='#2D8CFF', font=('Segoe UI', 13), relief='flat', highlightthickness=1, highlightbackground='#3C3C3C')
        self.users_listbox.pack(fill='x', padx=8, pady=8)
    
    def create_chat_panel(self, parent):
        """Create chat panel with embedded Online Users"""
        frame = tk.LabelFrame(parent, text="Group Chat", bg='#232323',
                             fg='#FFFFFF', font=('Segoe UI', 14, 'bold'), bd=0, labelanchor='nw')
        frame.pack(fill='both', expand=True, pady=8, padx=8)

        # Online Users list will be shown via a toggle near the input (hidden by default)
        self._users_visible = False
        self.users_section = tk.Frame(frame, bg='#232323')
        # Do not pack initially; packed on toggle

        # Mode label above chat (Group vs Private)
        self.chat_mode_label = tk.Label(frame, text="Group Chat", bg='#232323', fg='#A1A1A1', font=('Segoe UI', 12, 'italic'))
        self.chat_mode_label.pack(anchor='w', padx=8, pady=(6, 0))

        self.chat_display = scrolledtext.ScrolledText(frame, height=1, bg='#1C1C1C',
                                                       fg='#FFFFFF', font=('Segoe UI', 14),
                                                       wrap='word', state='disabled', relief='flat')
        self.chat_display.pack(fill='both', expand=True, padx=8, pady=8)
        
        input_frame = tk.Frame(frame, bg='#232323')
        input_frame.pack(fill='x', padx=8, pady=8)
        
        self.chat_input = tk.Entry(input_frame, bg='#1C1C1C', fg='#FFFFFF',
                                   font=('Segoe UI', 14), insertbackground='#FFFFFF', relief='solid', bd=1, highlightthickness=0)
        self.chat_input.pack(side='left', fill='x', expand=True, padx=(0, 8), ipady=8)
        self.chat_input.bind('<Return>', lambda e: self.send_chat())
        
        # Users toggle icon button (people)
        users_btn = tk.Button(input_frame, text="👥", bg=self._brand_blue, fg='#FFFFFF',
                 command=self.toggle_users_panel, padx=14, pady=10, relief='flat', bd=0, activeforeground='#FFFFFF', cursor='hand2')
        users_btn.pack(side='right', padx=(0, 6))
        self._style_primary(users_btn)

        # Upload icon button (paperclip)
        upload_btn = tk.Button(input_frame, text="📎", bg=self._brand_blue, fg='#FFFFFF',
                 command=self.upload_file, padx=14, pady=10, relief='flat', bd=0, activeforeground='#FFFFFF', cursor='hand2')
        upload_btn.pack(side='right', padx=(0, 6))
        self._style_primary(upload_btn)

        # Send icon button (send arrow)
        send_btn = tk.Button(input_frame, text="➤", bg=self._brand_blue, fg='#FFFFFF',
                 command=self.send_chat, padx=14, pady=10, relief='flat', bd=0, activeforeground='#FFFFFF', cursor='hand2')
        send_btn.pack(side='right', padx=(0, 6))
        self._style_primary(send_btn)
        
        # Build hidden users list inside users_section
        users_header = tk.Frame(self.users_section, bg='#232323')
        users_header.pack(fill='x', padx=8, pady=(0, 0))
        tk.Label(users_header, text="Online Users", bg='#232323', fg='#A1A1A1', font=('Segoe UI', 12, 'bold')).pack(anchor='w')
        self.users_listbox = tk.Listbox(self.users_section, height=5, bg='#1C1C1C', fg='#FFFFFF',
                                        selectbackground='#2D8CFF', font=('Segoe UI', 13), relief='flat', highlightthickness=1, highlightbackground='#3C3C3C')
        self.users_listbox.pack(fill='x', padx=8, pady=8)
        self.users_listbox.bind('<<ListboxSelect>>', self._on_user_selected)
    
    # Removed separate file panel; file sharing is integrated within chat
    
    def connect_to_server(self):
        """Connect to server"""
        server = self.server_entry.get().strip()
        username = self.username_entry.get().strip()
        
        if not server or not username:
            self.status_label.config(text="Enter server IP and username")
            return
        
        self.username = username
        result = self.network.connect(server, username)
        
        if result == True or (isinstance(result, tuple) and result[0]):
            # Initialize media handler
            self.media = MediaHandler(self.network, self)
            
            # Switch to main interface
            try:
                if hasattr(self, 'connection_wrapper'):
                    self.connection_wrapper.place_forget()
                else:
                    self.connection_frame.place_forget()
            except Exception:
                pass
            # Keep background for main application as well; do not destroy
            self.main_frame.pack(fill='both', expand=True)
            self.username_label.config(text=f"User: {self.username}")
            
            # Start update loops
            self.update_video_display()
            self.update_video_receive()
        else:
            error = result[1] if isinstance(result, tuple) else "Connection failed"
            self.status_label.config(text=error)
    
    def update_video_receive(self):
        """Continuously receive video frames"""
        if not self.network.running:
            return
        
        frames = self.media.receive_video_frames()
        
        with self.video_lock:
            for username, frame in frames.items():
                self.received_videos[username] = frame
        
        self.root.after(10, self.update_video_receive)
    
    def update_video_display(self):
        """Update video display"""
        if not self.network.running:
            return
        
        try:
            canvas_width = self.video_canvas.winfo_width()
            canvas_height = self.video_canvas.winfo_height()
            
            if canvas_width > 1:
                self.video_canvas.delete('all')
                
                with self.video_lock:
                    videos = list(self.received_videos.items())
                
                # Add local video
                if self.local_video_frame is not None:
                    videos.insert(0, (f"{self.username} (You)", self.local_video_frame))
                
                if videos:
                    # Draw inside a centered square region to avoid rectangular look
                    square_size = min(canvas_width, canvas_height)
                    offset_x = (canvas_width - square_size) // 2
                    offset_y = (canvas_height - square_size) // 2

                    cols = int(np.ceil(np.sqrt(len(videos))))
                    rows = int(np.ceil(len(videos) / cols))
                    
                    cell_w = square_size // cols
                    cell_h = square_size // rows
                    
                    for idx, (user, frame) in enumerate(videos):
                        row = idx // cols
                        col = idx % cols
                        x = offset_x + col * cell_w
                        y = offset_y + row * cell_h
                        
                        frame_resized = cv2.resize(frame, (max(1, cell_w-10), max(1, cell_h-30)))
                        frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
                        img = Image.fromarray(frame_rgb)
                        photo = ImageTk.PhotoImage(img)
                        
                        self.video_canvas.create_image(x+5, y+5, anchor='nw', image=photo)
                        self.video_canvas.create_text(x+cell_w//2, y+cell_h-10,
                                                     text=user, fill='#FFFFFF',
                                                     font=('Segoe UI', 13, 'bold'))
                        
                        if not hasattr(self, '_vid_refs'):
                            self._vid_refs = []
                        self._vid_refs.append(photo)
                    
                    self._vid_refs = self._vid_refs[-20:]  # Keep last 20
                else:
                    self.video_canvas.create_text(canvas_width//2, canvas_height//2,
                                                 text="No active video streams",
                                                 fill='#A1A1A1', font=('Segoe UI', 14))
                
                # Update screen sharing
                if self.screen_frame:
                    # Only update if it's a new frame (avoid redundant processing)
                    if self.screen_frame is not self.last_screen_frame:
                        self.last_screen_frame = self.screen_frame
                        
                        w = self.screen_canvas.winfo_width()
                        h = self.screen_canvas.winfo_height()
                        if w > 1 and h > 1:
                            # Draw the screen image proportionally to the canvas size (not forced square)
                            img = self.screen_frame.copy()
                            img_w, img_h = img.size
                            # Reserve header area (30px)
                            header_h = 30
                            avail_w = max(1, w - 20)
                            avail_h = max(1, h - header_h - 10)
                            scale = min(avail_w / img_w, avail_h / img_h)
                            new_w = max(1, int(img_w * scale))
                            new_h = max(1, int(img_h * scale))

                            img = img.resize((new_w, new_h), Image.LANCZOS)
                            photo = ImageTk.PhotoImage(img)

                            self.screen_canvas.delete('all')

                            # Center image below header
                            center_x = w // 2
                            center_y = header_h + (avail_h // 2)
                            self.screen_canvas.create_image(center_x, center_y, anchor='center', image=photo)

                            # Presenter header full width
                            presenter_text = f"{self.presenter_name}'s Screen" if self.presenter_name else "Screen Share"
                            self.screen_canvas.create_rectangle(0, 0, w, header_h, fill='#232323', outline='')
                            self.screen_canvas.create_text(w//2, header_h//2, text=presenter_text,
                                                          fill='#FFFFFF', font=('Segoe UI', 14, 'bold'))

                            self._screen_ref = photo
                else:
                    # Clear canvas when no presentation
                    if self.last_screen_frame is not None:
                        self.last_screen_frame = None
                        self.screen_canvas.delete('all')
                        # Show placeholder text
                        w = self.screen_canvas.winfo_width()
                        h = self.screen_canvas.winfo_height()
                        if w > 1:
                            self.screen_canvas.create_text(w//2, h//2,
                                                          text="No screen sharing active",
                                                          fill='#A1A1A1', font=('Segoe UI', 14))
        except Exception as e:
            print(f"Display error: {e}")
        
        self.root.after(33, self.update_video_display)
    
    def toggle_video(self):
        """Toggle video"""
        if not self.media:
            return
        
        if not self.media.video_streaming:
            success, msg = self.media.start_video()
            if success:
                self.video_btn.config(text="⏹ Stop Video")
                self._style_danger(self.video_btn)
            else:
                messagebox.showerror("Video Error", msg)
        else:
            self.media.stop_video()
            self.local_video_frame = None
            self.video_btn.config(text="🎥 Start Video")
            self._style_primary(self.video_btn)
    
    def toggle_audio(self):
        """Toggle audio"""
        if not self.media:
            return
        
        if not self.media.audio_streaming:
            success, msg = self.media.start_audio()
            if success:
                self.audio_btn.config(text="⏹ Stop Audio")
                self._style_danger(self.audio_btn)
            else:
                messagebox.showerror("Audio Error", msg)
        else:
            self.media.stop_audio()
            self.audio_btn.config(text="🎙 Start Audio")
            self._style_primary(self.audio_btn)
    
    def toggle_presentation(self):
        """Toggle presentation"""
        if not self.media:
            return
        
        if not self.media.presenting:
            print("[GUI] Starting presentation...")
            self.network.send_tcp_message({'type': 'start_presentation'})
            self.media.start_presentation()
            self.present_btn.config(text="⏹ Stop Presenting")
            self._style_danger(self.present_btn)
        else:
            print("[GUI] Stopping presentation...")
            self.network.send_tcp_message({'type': 'stop_presentation'})
            self.media.stop_presentation()
            self.present_btn.config(text="🖥 Start Presenting")
            self._style_primary(self.present_btn)
            self.screen_frame = None  # Clear screen frame when stopping
    
    def send_chat(self):
        """Send chat message"""
        msg = self.chat_input.get().strip()
        if msg and self.network.connected:
            # Group or private depending on mode
            if getattr(self, 'current_chat_target', None):
                self.network.send_tcp_message({
                    'type': 'private_chat',
                    'to': self.current_chat_target,
                    'message': msg
                })
                # Immediate local echo for responsiveness
                try:
                    self.add_chat(f"[Private ➜ {self.current_chat_target}]", msg, '#FFD166')
                except Exception:
                    pass
            else:
                self.network.send_tcp_message({
                    'type': 'chat',
                    'message': msg
                })
            self.chat_input.delete(0, tk.END)
    
    def upload_file(self):
        """Upload file"""
        filepath = filedialog.askopenfilename(title="Select File to Upload")
        if filepath:
            try:
                with open(filepath, 'rb') as f:
                    data = f.read()
                
                filename = os.path.basename(filepath)
                file_id = f"{self.username}_{int(datetime.now().timestamp())}_{filename}"
                
                self.network.send_tcp_message({
                    'type': 'file_upload',
                    'file_id': file_id,
                    'filename': filename,
                    'size': len(data),
                    'data': base64.b64encode(data).decode('utf-8')
                })
                
                messagebox.showinfo("Upload", f"File '{filename}' uploaded successfully")
            except Exception as e:
                messagebox.showerror("Upload Error", str(e))
    
    def download_file(self, file_id):
        """Request download for a given file_id"""
        if not file_id:
            return
        def _send():
            try:
                self.network.send_tcp_message({'type': 'file_download', 'file_id': file_id})
            except Exception as e:
                # Surface error without killing app
                self.root.after(0, lambda err=e: messagebox.showerror("Download Error", str(err)))
        t = threading.Thread(target=_send, daemon=True)
        t.start()

    def _insert_clickable_file_message(self, uploader, filename, file_id, size):
        """Insert a clickable file entry inside the chat log"""
        self.chat_display.config(state='normal')
        ts = datetime.now().strftime('%H:%M:%S')
        tag = f"file_{file_id}"
        display_text = f"[{ts}] {uploader} shared: "
        self.chat_display.insert(tk.END, display_text)
        start_index = self.chat_display.index(tk.INSERT)
        self.chat_display.insert(tk.END, f"📎 {filename} ({size} B)\n", tag)
        end_index = self.chat_display.index(tk.INSERT)

        # Style and bind click
        self.chat_display.tag_config(tag, foreground='#2D8CFF', underline=True)
        def on_click(event, fid=file_id):
            try:
                self.download_file(fid)
            except Exception as e:
                messagebox.showerror("Download Error", str(e))
        self.chat_display.tag_bind(tag, '<Button-1>', on_click)

        # Subtle timestamp color
        self.chat_display.tag_config('ts', foreground='#A1A1A1')
        self.chat_display.see(tk.END)
        self.chat_display.config(state='disabled')
    
    # Callback methods
    def on_server_message(self, msg):
        """Handle server messages"""
        msg_type = msg.get('type')
        
        if msg_type == 'welcome':
            self.add_chat("System", msg['message'], '#3FB950')
            self.update_users(msg.get('users', []))
        
        elif msg_type == 'user_joined':
            self.add_chat("System", f"{msg['username']} joined", '#2D8CFF')
            self.update_users(msg.get('users', []))
        
        elif msg_type == 'user_left':
            self.add_chat("System", f"{msg['username']} left", '#E74C3C')
            self.update_users(msg.get('users', []))
            with self.video_lock:
                self.received_videos.pop(msg['username'], None)
        
        elif msg_type == 'chat':
            self.add_chat(msg['username'], msg['message'])
        
        elif msg_type == 'private_chat':
            # Display private messages distinctly
            sender = (msg.get('from') or '').strip()
            recipient = (msg.get('to') or '').strip()
            text = msg.get('message', '')
            print(f"[GUI PM] from={sender} to={recipient} text={text}")
            me = (self.username or '').strip()
            if sender.lower() == me.lower():
                label = f"[Private ➜ {recipient}]"
                color = '#FFD166'  # amber
                self.add_chat(label, text, color)
            elif recipient.lower() == me.lower():
                label = f"[Private from {sender}]"
                color = '#FFD166'
                self.add_chat(label, text, color)
        
        elif msg_type == 'presentation_started':
            self.presenter_name = msg['username']
            presenter_msg = "You are presenting" if msg['username'] == self.username else f"{msg['username']} is presenting"
            self.add_chat("System", presenter_msg, '#2D8CFF')
            # Update Present button state for all clients
            if hasattr(self, 'present_btn'):
                if msg['username'] == self.username:
                    # You are the presenter
                    self.present_btn.config(text="⏹ Stop Presenting", state='normal')
                    self._style_danger(self.present_btn)
                else:
                    # Someone else is presenting; disable your ability to start
                    self.present_btn.config(text=f"{msg['username']} is screen sharing", state='disabled')
                    self._style_disabled(self.present_btn)
        
        elif msg_type == 'presentation_stopped':
            stop_msg = "You stopped presenting" if self.presenter_name == self.username else f"{self.presenter_name} stopped presenting"
            self.add_chat("System", stop_msg, '#2D8CFF')
            self.presenter_name = None
            self.screen_frame = None
            # Restore Present button for everyone not presenting
            if hasattr(self, 'present_btn'):
                self.present_btn.config(text="🖥 Start Presenting", state='normal')
                self._style_primary(self.present_btn)
            # Canvas will be cleared automatically
        
        elif msg_type == 'screen_frame':
            try:
                from io import BytesIO
                frame_id = msg.get('frame_id')
                data_b64 = msg['frame_data']
                print(f"[SCREEN] Incoming frame: base64 bytes={len(data_b64)}, from {msg.get('username', 'unknown')} frame_id={frame_id}")
                data = base64.b64decode(data_b64)
                try:
                    img = Image.open(BytesIO(data))
                    img.load()  # Force loading to catch errors
                except Exception as e:
                    print(f"[SCREEN] Error decoding frame (not PNG/JPG?): {e}")
                    return
                # If already showing this frame, skip update
                if getattr(self, '_last_screen_frame_id', None) == frame_id:
                    return
                self.screen_frame = img
                self._last_screen_frame_id = frame_id
                print(f"[SCREEN] Received decoded frame: size={img.size} mode={img.mode}")
            except Exception as e:
                print(f"[SCREEN] Error decoding screen frame: {e}")
                import traceback
                traceback.print_exc()
        
        elif msg_type == 'file_available':
            self.available_files[msg['file_id']] = {
                'filename': msg['filename'],
                'size': msg['size'],
                'uploader': msg['uploader']
            }
            # Insert clickable file entry directly in chat
            self.root.after(0, lambda: self._insert_clickable_file_message(
                msg['uploader'], msg['filename'], msg['file_id'], msg['size']
            ))
        
        elif msg_type == 'file_data':
            try:
                filename = msg['filename']
                data = base64.b64decode(msg['data'])
                # Run dialog and file write on the main thread to avoid crashes
                self.root.after(0, lambda: self._handle_file_save(filename, data))
            except Exception as e:
                self.root.after(0, lambda err=e: messagebox.showerror("Download Error", str(err)))
    
    def on_local_video_frame(self, frame):
        """Callback for local video frame"""
        self.local_video_frame = frame
    
    def on_local_screen_frame(self, frame):
        """Callback for local screen frame (presenter sees their own screen)"""
        self.screen_frame = frame
    
    def on_disconnected(self):
        """Handle disconnection"""
        self.root.after(0, lambda: messagebox.showerror("Disconnected",
                       "Lost connection to server"))
        self.root.after(0, self.on_closing)
    
    def update_users(self, users):
        """Update users list"""
        self.root.after(0, lambda: self._update_users(users))
    
    def _update_users(self, users):
        """Internal update users"""
        if hasattr(self, 'users_listbox'):
            self.users_listbox.delete(0, tk.END)
            for user in users:
                prefix = '● ' if user == self.username else '  '
                self.users_listbox.insert(tk.END, f"{prefix}{user}")

    def _on_user_selected(self, event):
        """Toggle private chat mode when selecting a user in the list."""
        try:
            selection = self.users_listbox.curselection()
            if not selection:
                return
            raw = self.users_listbox.get(selection[0])
            name = raw.strip()
            if name.startswith('●'):
                name = name[1:].strip()
            if name == self.username:
                # Selecting self returns to group chat
                self.current_chat_target = None
                self.chat_mode_label.config(text="Group Chat")
                return
            # Toggle if clicking same user again
            if getattr(self, 'current_chat_target', None) == name:
                self.current_chat_target = None
                self.chat_mode_label.config(text="Group Chat")
                self.add_chat("System", "Switched to Group Chat", '#2D8CFF')
            else:
                self.current_chat_target = name
                self.chat_mode_label.config(text=f"Private to {name}")
                self.add_chat("System", f"Private messaging {name}", '#2D8CFF')
        except Exception as e:
            print(f"User select error: {e}")
    
    def add_chat(self, username, message, color='#ecf0f1'):
        """Add chat message"""
        self.root.after(0, lambda: self._add_chat(username, message, color))
    
    def _add_chat(self, username, message, color):
        """Internal add chat"""
        self.chat_display.config(state='normal')
        ts = datetime.now().strftime('%H:%M:%S')
        
        if username == "System":
            self.chat_display.insert(tk.END, f"[{ts}] ", 'ts')
            self.chat_display.insert(tk.END, f"{message}\n", 'sys')
            self.chat_display.tag_config('sys', foreground=color, font=('Segoe UI', 14, 'italic'))
        else:
            self.chat_display.insert(tk.END, f"[{ts}] ", 'ts')
            self.chat_display.insert(tk.END, f"{username}: ", 'user')
            self.chat_display.insert(tk.END, f"{message}\n")
            self.chat_display.tag_config('user', foreground='#2D8CFF', font=('Segoe UI', 14, 'bold'))
        
        self.chat_display.tag_config('ts', foreground='#A1A1A1')
        self.chat_display.see(tk.END)
        self.chat_display.config(state='disabled')
    
    def toggle_users_panel(self):
        """Show/hide the embedded Online Users list inside chat"""
        self._users_visible = not getattr(self, '_users_visible', False)
        if self._users_visible:
            # Show below the input, before auto-scroll area end
            self.users_section.pack(fill='x', padx=8, pady=(0, 8))
        else:
            self.users_section.pack_forget()
    
    # File list UI removed; downloads are triggered from clickable chat entries
    
    def on_closing(self):
        """Handle window closing"""
        if self.media:
            if self.media.video_streaming:
                self.media.stop_video()
            if self.media.audio_streaming:
                self.media.stop_audio()
        
        if self.network:
            self.network.disconnect()
        
        self.root.destroy()
    
    def run(self):
        """Run the application"""
        self.root.mainloop()

    def _on_right_section_resize(self, event):
        """Size screen share row to match current screen frame aspect; chat gets remaining space."""
        try:
            if not hasattr(self, 'right_section'):
                return
            width = max(0, self.right_section.winfo_width())
            header_h = 30
            # Determine aspect ratio from current screen frame if available; fallback to 16:9
            aspect_h_over_w = None
            if getattr(self, 'screen_frame', None) is not None:
                try:
                    img_w, img_h = self.screen_frame.size
                    if img_w > 0:
                        aspect_h_over_w = img_h / img_w
                except Exception:
                    aspect_h_over_w = None
            if aspect_h_over_w is None:
                aspect_h_over_w = 9/16
            desired_h = int(width * aspect_h_over_w) + header_h
            self.right_section.grid_rowconfigure(0, minsize=desired_h)
            # Ensure chat row stretches to fill remaining space
            self.right_section.grid_rowconfigure(1, weight=1)
        except Exception as e:
            print(f"Resize error: {e}")

    def _handle_file_save(self, filename, data_bytes):
        """Open save dialog and write file safely on the main thread."""
        try:
            save_path = filedialog.asksaveasfilename(
                defaultextension=os.path.splitext(filename)[1],
                initialfile=filename
            )
            if save_path:
                with open(save_path, 'wb') as f:
                    f.write(data_bytes)
                messagebox.showinfo("Download", f"Saved to {save_path}")
        except Exception as e:
            messagebox.showerror("Download Error", str(e))
