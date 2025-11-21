import socket
import json
import logging
import struct
import time
import traceback
from abc import abstractmethod
from typing import Optional, List

from PyQt6.QtCore import QMutex, QThread, pyqtSignal, pyqtSlot, QByteArray, QSize, Qt
from PyQt6.QtGui import QImage
from PyQt6.QtCore import QSettings

import remotex_viewer.remotex as remotex
from .protocol import *

logger = logging.getLogger(__name__)

from enum import Enum, auto

class ArcaneProtocolError(Enum):
    AuthenticationFailed = auto()
    ResourceNotFound = auto()
    InvalidStructureData = auto()
    UnsupportedVersion = auto()
    MissingServerCertificate = auto()
    MissingSession = auto()
    ServerFingerprintTampered = auto()

class ArcaneProtocolException(Exception):
    def __init__(self, reason: ArcaneProtocolError) -> None:
        self.reason = reason
        super().__init__(str(reason))

class Screen:
    def __init__(self, screen_information_json: dict) -> None:
        self.id = screen_information_json.get("Id", 0)
        self.name = screen_information_json.get("Name", "Screen")
        self.width = screen_information_json.get("Width", 1920)
        self.height = screen_information_json.get("Height", 1080)
        self.x = screen_information_json.get("X", 0)
        self.y = screen_information_json.get("Y", 0)
        self.primary = screen_information_json.get("Primary", True)

    def size(self) -> QSize:
        return QSize(self.width, self.height)

class Client:
    def __init__(self, server_address: str, server_port: int, password: str) -> None:
        self.server_address = server_address
        self.server_port = server_port
        self.password = password
        self.conn = None
        
        self.connect()

    def connect(self):
        logger.info(f"Connecting to {self.server_address}:{self.server_port}...")
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn.connect((self.server_address, self.server_port))
        
        # Handshake
        banner = self.read_line()
        if banner != "ArcaneServer":
            raise Exception("Invalid Server Banner")
            
        self.write_line(self.password)
        response = self.read_line()
        if response != "OK":
            raise Exception("Authentication Failed")
            
        logger.info("Connected and Authenticated")

    def read_line(self) -> str:
        data = b""
        while True:
            chunk = self.conn.recv(1)
            if not chunk: break
            data += chunk
            if chunk == b'\n': break
        return data.decode().strip()

    def write_line(self, line: str) -> None:
        self.conn.sendall(line.encode() + b'\n')

    def read_json(self) -> dict:
        return json.loads(self.read_line())

    def write_json(self, data: dict) -> None:
        self.write_line(json.dumps(data))

    def close(self):
        if self.conn:
            self.conn.close()

class Session:
    def __init__(self, server_address: str, server_port: int, password: str) -> None:
        self.server_address = server_address
        self.server_port = server_port
        self.password = password
        self.session_id = None
        self.display_name = "Remote"
        self.presentation = False
        
        settings = QSettings(remotex.APP_ORGANIZATION_NAME, remotex.APP_NAME)
        self.clipboard_mode = settings.value(remotex.SETTINGS_KEY_CLIPBOARD_MODE, ClipboardMode.Both)
        self.option_image_quality = settings.value(remotex.SETTINGS_KEY_IMAGE_QUALITY, 80)
        self.option_packet_size = settings.value(remotex.SETTINGS_KEY_PACKET_SIZE, PacketSize.Size4096)

        self.request_session()

    def request_session(self):
        client = Client(self.server_address, self.server_port, self.password)
        try:
            client.write_line("RequestSession")
            info = client.read_json()
            self.session_id = info["SessionId"]
            self.display_name = f"{info['Username']}@{info['MachineName']}"
        finally:
            client.close()

    def claim_client(self, worker_kind: WorkerKind) -> Client:
        client = Client(self.server_address, self.server_port, self.password)
        client.write_line("AttachToSession")
        client.write_line(self.session_id)
        resp = client.read_line()
        if resp != "ResourceFound":
            raise Exception("Session not found")
        client.write_line(worker_kind.name)
        return client

class ClientBaseThread(QThread):
    thread_finished = pyqtSignal(bool)

    def __init__(self, session: Session, worker_kind: WorkerKind) -> None:
        super().__init__()
        self._running = True
        self._connected = False
        self._mutex = QMutex()
        self.session = session
        self.client: Optional[Client] = None
        self.worker_kind = worker_kind

    def run(self) -> None:
        on_error = False
        try:
            self.client = self.session.claim_client(self.worker_kind)
            self._connected = True
            self.client_execute()
        except Exception as e:
            if self._running:
                logger.error(f"Thread error: {e}")
                traceback.print_exc()
                on_error = True
        finally:
            self.stop()
            self.thread_finished.emit(on_error)

    @abstractmethod
    def client_execute(self) -> None:
        pass

    @pyqtSlot()
    def stop(self) -> None:
        self._mutex.lock()
        try:
            if self.client:
                self.client.close()
            self._running = False
        finally:
            self._mutex.unlock()

class VirtualDesktopThread(ClientBaseThread):
    open_cellar_door = pyqtSignal(Screen)
    received_dirty_rect_signal = pyqtSignal(QImage, int, int)
    start_events_worker_signal = pyqtSignal()

    def __init__(self, session: Session) -> None:
        super().__init__(session, WorkerKind.Desktop)
        self.selected_screen: Optional[Screen] = None

    def client_execute(self) -> None:
        if not self.client: return
        
        # Send params
        self.client.write_json({
            "ScreenName": "Primary",
            "ImageCompressionQuality": self.session.option_image_quality,
            "PacketSize": self.session.option_packet_size.value
        })
        
        # Fake screen info for UI
        self.selected_screen = Screen({"Name": "Primary", "Width": 1920, "Height": 1080}) # Ideally we get this from server
        self.open_cellar_door.emit(self.selected_screen)
        self.start_events_worker_signal.emit()

        while self._running:
            try:
                header = self.client.conn.recv(13)
                if len(header) < 13: break
                chunk_size, x, y, updated = struct.unpack('IIIB', header)
                
                data = b""
                while len(data) < chunk_size:
                    packet = self.client.conn.recv(min(4096, chunk_size - len(data)))
                    if not packet: break
                    data += packet
                
                img = QImage()
                img.loadFromData(QByteArray(data))
                self.received_dirty_rect_signal.emit(img, x, y)
            except Exception:
                break

class EventsThread(ClientBaseThread):
    update_mouse_cursor = pyqtSignal(Qt.CursorShape)
    update_clipboard = pyqtSignal(str)

    def __init__(self, session: Session) -> None:
        super().__init__(session, WorkerKind.Events)

    def client_execute(self) -> None:
        if not self.client: return
        while self._running:
            try:
                # We don't expect much from server in simple mode, maybe clipboard
                # Server sends JSON lines
                pass # Implement reading if needed
            except Exception:
                break

    @pyqtSlot(int, int, MouseState, MouseButton)
    def send_mouse_event(self, x: int, y: int, state: MouseState, button: MouseButton) -> None:
        if self.client:
            self.client.write_json({
                "Id": OutputEvent.MouseClickMove.value,
                "X": x, "Y": y,
                "Button": button.name,
                "Type": state.value
            })

    @pyqtSlot(str)
    def send_key_event(self, keys: str, is_shortcut: bool) -> None:
        if self.client:
            self.client.write_json({
                "Id": OutputEvent.Keyboard.value,
                "IsShortcut": is_shortcut,
                "Keys": keys
            })

    @pyqtSlot(int)
    def send_mouse_wheel_event(self, delta: int) -> None:
        if self.client:
            self.client.write_json({
                "Id": OutputEvent.MouseWheel.value,
                "Delta": delta
            })

    @pyqtSlot(str)
    def send_clipboard_text(self, text: str) -> None:
        if self.client:
            self.client.write_json({
                "Id": OutputEvent.ClipboardUpdated.value,
                "Text": text
            })

class ConnectThread(QThread):
    thread_started = pyqtSignal()
    thread_finished = pyqtSignal(object)
    session_error = pyqtSignal(str)

    def __init__(self, server_address: str, server_port: int, password: str) -> None:
        super().__init__()
        self.server_address = server_address
        self.server_port = server_port
        self.password = password

    def run(self) -> None:
        session = None
        self.thread_started.emit()
        try:
            session = Session(self.server_address, self.server_port, self.password)
        except Exception as e:
            logger.error(f"Connection error: {e}")
            self.session_error.emit(str(e))
        finally:
            self.thread_finished.emit(session)
