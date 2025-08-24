import threading
import ctypes
from ctypes import wintypes
from datetime import datetime
import sqlite3
import os


# Константы и WinAPI
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

PIPE_ACCESS_DUPLEX = 0x00000003
PIPE_TYPE_MESSAGE = 0x00000004
PIPE_READMODE_MESSAGE = 0x00000002
PIPE_WAIT = 0x00000000
PIPE_UNLIMITED_INSTANCES = 255

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3

PIPE_NAME = r"\\.\pipe\logger"
PIPE_BUFFER_SIZE = 65536
READ_BUFFER = 4096
DB_PATH = os.path.join(os.path.dirname(__file__), 'logger.db')

# События/протокол
EVENT_TYPES = {
    'REGISTER': 'REGISTER',
    'ACTIVE': 'Active',
    'IDLE': 'Idle',
    'STARTED': 'Started',
    'STOPPED': 'Stopped',
    'TYPING': 'Typing',
    'COMPUTING': 'Computing'
}

PROTOCOL_MESSAGES = {
    'TYPING_START': 'Начало ввода',
    'TYPING_END': 'Конец ввода',
    'TEXT_INPUT_PREFIX': "Введен текст '",
}


def _last_error():
    return ctypes.get_last_error()


def read_message(h):
    buf = ctypes.create_string_buffer(READ_BUFFER)
    read = wintypes.DWORD()
    ok = kernel32.ReadFile(h, buf, READ_BUFFER, ctypes.byref(read), None)
    if not ok:
        raise OSError(_last_error())
    return buf.raw[:read.value].decode(errors='ignore')


def write_message(h, s: str):
    data = s.encode()
    written = wintypes.DWORD()
    ok = kernel32.WriteFile(h, data, len(data), ctypes.byref(written), None)
    if not ok:
        raise OSError(_last_error())


class LoggerServer:
    def __init__(self):
        self.client_counter = 1
        self.lock = threading.Lock()
        self._init_db()

    # --- DB ---
    def _init_db(self):
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS clients (
                client_id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT UNIQUE,
                client_type TEXT
            )''')
            c.execute('''CREATE TABLE IF NOT EXISTS events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                client_id INTEGER,
                client_type TEXT,
                event_category TEXT,
                event_value TEXT
            )''')
            conn.commit()

    def _register_client(self, base_name: str, client_type: str) -> str:
        n = 1
        while True:
            name = f"{base_name}_{n}"
            try:
                with sqlite3.connect(DB_PATH, timeout=10) as conn:
                    c = conn.cursor()
                    c.execute('INSERT INTO clients (client_name, client_type) VALUES (?, ?)', (name, client_type))
                    conn.commit()
                return name
            except sqlite3.IntegrityError:
                n += 1

    def _save_event(self, client_id: int, client_type: str, category: str, value: str):
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            c = conn.cursor()
            c.execute('''INSERT INTO events (timestamp, client_id, client_type, event_category, event_value)
                         VALUES (?, ?, ?, ?, ?)''', (ts, client_id, client_type, category, value))
            conn.commit()

    # --- Event processing ---
    def _process_event(self, event_type: str, details: str):
        if event_type in (EVENT_TYPES['ACTIVE'], EVENT_TYPES['IDLE']):
            return 'status', event_type
        if event_type == EVENT_TYPES['STARTED']:
            return 'action', 'Started'
        if event_type == EVENT_TYPES['STOPPED']:
            return 'action', 'Finished'
        if event_type == EVENT_TYPES['TYPING']:
            if details == PROTOCOL_MESSAGES['TYPING_START']:
                return 'status', 'Typing started'
            if details == PROTOCOL_MESSAGES['TYPING_END']:
                return 'status', 'Typing ended'
            # text payload
            if details.startswith(PROTOCOL_MESSAGES['TEXT_INPUT_PREFIX']):
                try:
                    text = details.split("'", 2)[1]
                except Exception:
                    text = details
                return 'result', text
            return 'result', details
        if event_type == EVENT_TYPES['COMPUTING']:
            # статус начала/конца ввода
            if details in (PROTOCOL_MESSAGES['TYPING_START'], PROTOCOL_MESSAGES['TYPING_END']):
                return 'status', ('Typing started' if details == PROTOCOL_MESSAGES['TYPING_START'] else 'Typing ended')
            # результат уже прислан клиентом
            return 'result', details
        return 'result', details

    def _handle_client(self, pipe, client_id):
        try:
            # Ожидаем REGISTER:BaseName:Type
            data = read_message(pipe)
            if not data.startswith("REGISTER:"):
                return
            try:
                _, base_name, client_type = data.split(':', 2)
            except ValueError:
                return

            client_name = self._register_client(base_name, client_type)
            write_message(pipe, f"NAME:{client_name}:{client_id}")

            # Основной цикл
            while True:
                msg = read_message(pipe)
                try:
                    et, details = msg.split(':', 1)
                except ValueError:
                    continue
                category, value = self._process_event(et, details)
                self._save_event(client_id, client_type, category, value)
                ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print(f"[{ts}] [{client_id}] [{client_type}] {category}: {value}")
        except Exception:
            pass
        finally:
            try:
                kernel32.FlushFileBuffers(pipe)
                kernel32.DisconnectNamedPipe(pipe)
                kernel32.CloseHandle(pipe)
            except Exception:
                pass

    def start(self):
        print("Server started. Waiting for client connections...")
        while True:
            pipe = kernel32.CreateNamedPipeW(
                PIPE_NAME,
                PIPE_ACCESS_DUPLEX,
                PIPE_TYPE_MESSAGE | PIPE_READMODE_MESSAGE | PIPE_WAIT,
                PIPE_UNLIMITED_INSTANCES,
                PIPE_BUFFER_SIZE,
                PIPE_BUFFER_SIZE,
                0,
                None,
            )
            if pipe == ctypes.c_void_p(-1).value:
                raise OSError(_last_error())

            ok = kernel32.ConnectNamedPipe(pipe, None)
            if not ok:
                kernel32.CloseHandle(pipe)
                continue

            with self.lock:
                cid = self.client_counter
                self.client_counter += 1
            t = threading.Thread(target=self._handle_client, args=(pipe, cid), daemon=True)
            t.start()


if __name__ == '__main__':
    LoggerServer().start()


