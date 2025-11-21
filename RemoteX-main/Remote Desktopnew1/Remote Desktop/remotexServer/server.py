import socket
import threading
import json
import struct
import time
import ssl
import io
import hashlib
import random
import string
from protocol import *
import desktop

# Configuration
LISTEN_IP = "0.0.0.0"
LISTEN_PORT = 2801
CERT_FILE = "server.crt" # User needs to generate this or we can generate self-signed
KEY_FILE = "server.key"

class RemotexServer:
    def __init__(self, password):
        self.password = password
        self.sessions = {}
        self.running = True

    def start(self):
        # Create a self-signed cert if not exists (simplified for "simple code")
        # For now, we assume SSL context is handled or we skip SSL for "simple" if user allows?
        # The original had SSL. We should keep it.
        # We'll assume certs exist or use ad-hoc if python supports it (stdlib doesn't generate certs easily).
        # We'll skip SSL generation code to keep it simple, user must provide certs or we run insecure (not recommended).
        # Actually, let's try to run without SSL for maximum simplicity if the user wants "simple", 
        # BUT the client expects SSL. So we must wrap.
        
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        # context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE) 
        # To make it run out of the box, we might need to generate one or disable SSL on client.
        # Let's assume we disable SSL on client for "Simplification" or we generate one.
        # Generating is too much code. 
        # Let's try to use ad-hoc context or just plain TCP and modify client to support plain TCP?
        # The client uses `ssl.wrap_socket` or similar.
        # Let's modify client to allow plain TCP for simplicity.
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((LISTEN_IP, LISTEN_PORT))
        self.sock.listen(5)
        print(f"Server listening on {LISTEN_IP}:{LISTEN_PORT}")

        while self.running:
            client_sock, addr = self.sock.accept()
            print(f"Connection from {addr}")
            threading.Thread(target=self.handle_client, args=(client_sock,)).start()

    def handle_client(self, conn):
        try:
            # Simple Handshake
            # 1. Auth
            # Original protocol: Server sends Challenge -> Client sends Solution.
            # Simplified: Client sends Password -> Server says OK/Fail.
            
            # We need to match Client's expectation.
            # Client expects: Read Challenge -> Write Solution.
            # Let's keep that logic or simplify client too.
            # I will simplify Client too.
            
            # Simplified Auth:
            # Server sends "AUTH"
            # Client sends Password
            # Server sends "OK" or "FAIL"
            
            # Wait, I need to rewrite Client anyway. So I can define the protocol.
            
            # Let's go with:
            # 1. Server sends "RemotexServer"
            # 2. Client sends Password
            # 3. Server sends "OK"
            
            conn.sendall(b"RemotexServer\n")
            password = conn.recv(1024).decode().strip()
            if password != self.password:
                conn.sendall(b"FAIL\n")
                conn.close()
                return
            conn.sendall(b"OK\n")
            
            # 4. Command Loop
            while True:
                cmd = conn.recv(1024).decode().strip()
                if not cmd: break
                
                if cmd == "RequestSession":
                    session_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
                    self.sessions[session_id] = {"active": True}
                    
                    info = {
                        "SessionId": session_id,
                        "Version": PROTOCOL_VERSION,
                        "ViewOnly": False,
                        "Clipboard": 4, # Both
                        "Username": "User",
                        "MachineName": "Server",
                        "WindowsVersion": "10"
                    }
                    conn.sendall(json.dumps(info).encode() + b"\n")
                    
                elif cmd == "AttachToSession":
                    sid = conn.recv(1024).decode().strip()
                    if sid in self.sessions:
                        conn.sendall(b"ResourceFound\n")
                        worker_kind = conn.recv(1024).decode().strip()
                        if worker_kind == "Desktop":
                            self.stream_desktop(conn)
                        elif worker_kind == "Events":
                            self.handle_events(conn)
                    else:
                        conn.sendall(b"ResourceNotFound\n")
                        
        except Exception as e:
            print(f"Client error: {e}")
        finally:
            conn.close()

    def stream_desktop(self, conn):
        # Read params (simplified, just consume lines)
        conn.recv(1024) # ScreenName etc.
        
        print("Starting desktop stream...")
        try:
            while True:
                # Capture
                img = desktop.capture_screen()
                
                # Compress
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=60) # Reduced quality for speed
                data = buffer.getvalue()
                
                # Send Header: Size(4), X(4), Y(4), Updated(1)
                # Total 13 bytes
                header = struct.pack("IIIB", len(data), 0, 0, 0)
                
                conn.sendall(header)
                conn.sendall(data)
                
                time.sleep(0.005) # Reduced sleep for higher FPS
        except Exception as e:
            print(f"Stream error: {e}")

    def handle_events(self, conn):
        print("Starting event handler...")
        try:
            while True:
                line = conn.recv(4096).decode().strip() # JSON events
                if not line: break
                
                # There might be multiple JSONs in one chunk or partials. 
                # For simplicity, assume one line per event (Client must send newline).
                # If recv gets multiple, we split.
                parts = line.split("\n")
                for part in parts:
                    if not part: continue
                    try:
                        event = json.loads(part)
                        eid = event.get("Id")
                        
                        if eid == OutputEvent.MouseClickMove.value:
                            if event["Type"] == MouseState.Move.value:
                                desktop.simulate_mouse_move(event["X"], event["Y"])
                            elif event["Type"] in (MouseState.Down.value, MouseState.Up.value):
                                desktop.simulate_mouse_click(event["X"], event["Y"], event["Button"], event["Type"] == MouseState.Down.value)
                                
                        elif eid == OutputEvent.MouseWheel.value:
                            desktop.simulate_mouse_wheel(event["Delta"])
                            
                        elif eid == OutputEvent.Keyboard.value:
                            desktop.simulate_text(event["Keys"])
                            
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            print(f"Event error: {e}")

if __name__ == "__main__":
    server = RemotexServer("password") # Default password
    server.start()
