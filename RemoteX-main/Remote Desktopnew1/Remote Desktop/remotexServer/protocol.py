from enum import Enum, auto

PROTOCOL_VERSION = '5.0.2'

class WorkerKind(Enum):
    Desktop = 0x1
    Events = 0x2

class ClipboardMode(Enum):
    Disabled = 0x1
    Receive = 0x2
    Send = 0x3
    Both = 0x4

class RemotexProtocolCommand(Enum):
    Success = 0x1
    Fail = 0x2
    RequestSession = 0x3
    AttachToSession = 0x4
    BadRequest = 0x5
    ResourceFound = 0x6
    ResourceNotFound = 0x7

class OutputEvent(Enum):
    Keyboard = 0x1
    MouseClickMove = 0x2
    MouseWheel = 0x3
    KeepAlive = 0x4
    ClipboardUpdated = 0x5

class InputEvent(Enum):
    KeepAlive = 0x1
    MouseCursorUpdated = 0x2
    ClipboardUpdated = 0x3
    DesktopActive = 0x4
    DesktopInactive = 0x5

class MouseState(Enum):
    Up = 0x1
    Down = 0x2
    Move = 0x3

class MouseButton(Enum):
    Left = 0x1
    Right = 0x2
    Middle = 0x3
    Void = 0x4

class PacketSize(Enum):
    Size4096 = 4096
