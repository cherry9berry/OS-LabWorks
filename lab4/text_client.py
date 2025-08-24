import ctypes
from ctypes import wintypes
import tkinter as tk
from tkinter import ttk


kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3

PIPE_NAME = r"\\.\pipe\logger"
READ_BUFFER = 4096


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


class TextClient:
    def __init__(self):
        self.pipe = None
        self.root = tk.Tk()
        self.root.title("Text Client")
        self.client_name = None
        self.text_var = tk.StringVar()
        self.is_typing = False
        frm = ttk.Frame(self.root)
        frm.pack(padx=10, pady=10)
        entry = ttk.Entry(frm, textvariable=self.text_var, width=40)
        entry.pack(side=tk.LEFT)
        ttk.Button(frm, text="Send", command=self.on_send).pack(side=tk.LEFT, padx=5)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        # Событие начала/конца печати
        self.text_var.trace_add('write', self.on_text_change)

    def connect(self):
        self.pipe = kernel32.CreateFileW(
            PIPE_NAME,
            GENERIC_READ | GENERIC_WRITE,
            0,
            None,
            OPEN_EXISTING,
            0,
            None,
        )
        if self.pipe == ctypes.c_void_p(-1).value:
            raise OSError(_last_error())

    def register(self):
        write_message(self.pipe, "REGISTER:TextProcessor:Text")
        resp = read_message(self.pipe)
        assert resp.startswith("NAME:"), "registration failed"
        _, self.client_name, _ = resp.split(':', 2)
        # Started
        write_message(self.pipe, "Started:Text client started")

    def on_send(self):
        txt = self.text_var.get()
        if not txt:
            return
        write_message(self.pipe, f"TYPING:Введен текст '{txt}'")
        self.text_var.set("")

    def on_text_change(self, *args):
        txt = self.text_var.get()
        if len(txt) > 0 and not self.is_typing:
            write_message(self.pipe, "Typing:Начало ввода")
            self.is_typing = True
        elif len(txt) == 0 and self.is_typing:
            write_message(self.pipe, "Typing:Конец ввода")
            self.is_typing = False

    def _tick(self):
        # Active/Idle — без проверки активности окна, просто чередуем
        write_message(self.pipe, "Active:Active")
        self.root.after(10000, self._tick)

    def run(self):
        self.connect()
        self.register()
        self._tick()
        self.root.mainloop()

    def on_close(self):
        try:
            write_message(self.pipe, "Stopped:Text client stopped")
        except Exception:
            pass
        self.root.destroy()


if __name__ == '__main__':
    TextClient().run()


