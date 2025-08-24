import tkinter as tk
from tkinter import ttk
import platform
import os
import ctypes
from ctypes import wintypes
from collections import deque


# отрисовка графиков на Canvas
class GraphCanvas(ttk.Frame):
    def __init__(self, master, title: str, color: str = "#2e7d32", history: int = 120, height: int = 120):
        super().__init__(master)
        self.title = title
        self.color = color
        self.history_len = history
        self.height = height
        self.values = deque([0.0] * history, maxlen=history)

        self.header = ttk.Label(self, text=f"{self.title}: 0.0%")
        self.header.pack(anchor=tk.W)

        self.canvas = tk.Canvas(self, width=540, height=self.height, bg="white", highlightthickness=1, highlightbackground="#ddd")
        self.canvas.pack(fill=tk.X)

    def update_value(self, value: float):
        # Обновляем данные и перерисовываем
        value = max(0.0, min(100.0, float(value)))
        self.values.append(value)
        self.header.config(text=f"{self.title}: {value:.1f}%")
        self._redraw()

    def _redraw(self):
        self.canvas.delete("all")
        w = int(self.canvas.winfo_width())
        h = int(self.canvas.winfo_height())
        n = len(self.values)
        if n < 2:
            return

        # Сетка 25% шаг
        for i in range(1, 4):
            y = int(h * (i * 0.25))
            self.canvas.create_line(0, y, w, y, fill="#f0f0f0")
            self.canvas.create_text(20, y - 2, text=f"{i*25}%", fill="#888", anchor=tk.SW, font=("Segoe UI", 8))

        # Полилиния значений (по X равномерно, по Y масштаб 0..100%)
        step_x = max(1, w // (self.history_len - 1))
        points = []
        base_x = w - step_x * (self.history_len - 1)
        for idx, val in enumerate(self.values):
            x = base_x + idx * step_x
            y = int(h - (val / 100.0) * h)
            points.append((x, y))
        # Рисуем линию
        for i in range(1, len(points)):
            self.canvas.create_line(points[i - 1][0], points[i - 1][1], points[i][0], points[i][1], fill=self.color, width=2)


class SystemInfo(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        # Информация о системе (кратко)
        info = self._gather()

        rows = [
            ("OS", info["os"]),
            ("Architecture", info["arch"]),
            ("Logical cores", str(info["cores_logical"])),
            ("RAM total (GB)", f"{info['ram_total_gb']:.2f}"),
        ]

        grid = ttk.Frame(self)
        grid.pack(fill=tk.X)
        for r, (k, v) in enumerate(rows):
            ttk.Label(grid, text=f"{k}:").grid(row=r, column=0, sticky=tk.W, padx=4, pady=2)
            ttk.Label(grid, text=v).grid(row=r, column=1, sticky=tk.W, padx=4, pady=2)

    def _gather(self):
        # WinAPI: GlobalMemoryStatusEx + GetSystemInfo (Windows-only)
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ('dwLength', wintypes.DWORD),
                ('dwMemoryLoad', wintypes.DWORD),
                ('ullTotalPhys', ctypes.c_ulonglong),
                ('ullAvailPhys', ctypes.c_ulonglong),
                ('ullTotalPageFile', ctypes.c_ulonglong),
                ('ullAvailPageFile', ctypes.c_ulonglong),
                ('ullTotalVirtual', ctypes.c_ulonglong),
                ('ullAvailVirtual', ctypes.c_ulonglong),
                ('ullAvailExtendedVirtual', ctypes.c_ulonglong),
            ]
        class SYSTEM_INFO(ctypes.Structure):
            _fields_ = [
                ('wProcessorArchitecture', wintypes.WORD),
                ('wReserved', wintypes.WORD),
                ('dwPageSize', wintypes.DWORD),
                ('lpMinimumApplicationAddress', ctypes.c_void_p),
                ('lpMaximumApplicationAddress', ctypes.c_void_p),
                ('dwActiveProcessorMask', ctypes.c_void_p),
                ('dwNumberOfProcessors', wintypes.DWORD),
                ('dwProcessorType', wintypes.DWORD),
                ('dwAllocationGranularity', wintypes.DWORD),
                ('wProcessorLevel', wintypes.WORD),
                ('wProcessorRevision', wintypes.WORD),
            ]
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        ms = MEMORYSTATUSEX()
        ms.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        kernel32.GlobalMemoryStatusEx(ctypes.byref(ms))
        total_gb = ms.ullTotalPhys / (1024 ** 3)
        si = SYSTEM_INFO()
        kernel32.GetSystemInfo(ctypes.byref(si))
        cores = int(si.dwNumberOfProcessors)
        arch_map = {0: 'x86', 5: 'ARM', 6: 'IA64', 9: 'x64', 12: 'ARM64'}
        arch = arch_map.get(si.wProcessorArchitecture, platform.machine())
        return {
            "os": f"{platform.system()} {platform.release()}",
            "arch": arch,
            "cores_logical": cores,
            "ram_total_gb": total_gb,
        }


class MonitorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("System Monitor (Lab 1)")
        self.geometry("800x600")

        # Параметры обновления
        self.update_ms = 1000
        # Диск по умолчанию: C:\ на Windows, иначе /
        self.disk_path = 'C:\\' if os.name == 'nt' else '/'

        # Информация о системе
        info = SystemInfo(self)
        info.pack(fill=tk.X, padx=10)

        # Графики
        graphs = ttk.Frame(self)
        graphs.pack(fill=tk.BOTH, expand=True, padx=10, pady=(8, 10))

        self.cpu_graph = GraphCanvas(graphs, "CPU", color="#1976d2")
        self.mem_graph = GraphCanvas(graphs, "Memory", color="#d32f2f")
        self.disk_graph = GraphCanvas(graphs, "Disk", color="#388e3c")

        self.cpu_graph.pack(fill=tk.X, pady=8)
        self.mem_graph.pack(fill=tk.X, pady=8)
        self.disk_graph.pack(fill=tk.X, pady=8)

        # Подготовка для CPU (WinAPI)
        self._last_idle = None
        self._last_kernel = None
        self._last_user = None
        # Автообновление без кнопок
        self._tick()

    def _tick(self):
        # Сбор метрик
        cpu = self._cpu_percent()
        mem = self._memory_percent()
        try:
            disk_val = self._disk_percent()
        except Exception:
            disk_val = 0.0

        self.cpu_graph.update_value(cpu)
        self.mem_graph.update_value(mem)
        self.disk_graph.update_value(disk_val)

        # Следующее обновление
        self.after(self.update_ms, self._tick)

    # --- Метрики через WinAPI (Windows) ---
    def _cpu_percent(self) -> float:
        class FILETIME(ctypes.Structure):
            _fields_ = [('dwLowDateTime', wintypes.DWORD), ('dwHighDateTime', wintypes.DWORD)]
        idle, kernel, user = FILETIME(), FILETIME(), FILETIME()
        ok = ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user))
        if not ok:
            return 0.0
        def to_int(ft: FILETIME) -> int:
            return (ft.dwHighDateTime << 32) | ft.dwLowDateTime
        idle_i, kernel_i, user_i = to_int(idle), to_int(kernel), to_int(user)
        if self._last_idle is None:
            self._last_idle, self._last_kernel, self._last_user = idle_i, kernel_i, user_i
            return 0.0
        didle = idle_i - self._last_idle
        dkernel = kernel_i - self._last_kernel
        duser = user_i - self._last_user
        self._last_idle, self._last_kernel, self._last_user = idle_i, kernel_i, user_i
        total = dkernel + duser
        busy = total - didle
        return max(0.0, min(100.0, (busy * 100.0 / total) if total > 0 else 0.0))

    def _memory_percent(self) -> float:
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ('dwLength', wintypes.DWORD),
                ('dwMemoryLoad', wintypes.DWORD),
                ('ullTotalPhys', ctypes.c_ulonglong),
                ('ullAvailPhys', ctypes.c_ulonglong),
                ('ullTotalPageFile', ctypes.c_ulonglong),
                ('ullAvailPageFile', ctypes.c_ulonglong),
                ('ullTotalVirtual', ctypes.c_ulonglong),
                ('ullAvailVirtual', ctypes.c_ulonglong),
                ('ullAvailExtendedVirtual', ctypes.c_ulonglong),
            ]
        ms = MEMORYSTATUSEX()
        ms.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms)):
            return float(ms.dwMemoryLoad)
        return 0.0

    def _disk_percent(self) -> float:
        spc = wintypes.DWORD()
        bps = wintypes.DWORD()
        free_clusters = wintypes.DWORD()
        total_clusters = wintypes.DWORD()
        ok = ctypes.windll.kernel32.GetDiskFreeSpaceW(self.disk_path, ctypes.byref(spc), ctypes.byref(bps), ctypes.byref(free_clusters), ctypes.byref(total_clusters))
        if not ok or total_clusters.value == 0:
            return 0.0
        bytes_per_cluster = spc.value * bps.value
        total_bytes = total_clusters.value * bytes_per_cluster
        free_bytes = free_clusters.value * bytes_per_cluster
        used = total_bytes - free_bytes
        return max(0.0, min(100.0, (used * 100.0 / total_bytes) if total_bytes > 0 else 0.0))


if __name__ == "__main__":
    app = MonitorApp()
    app.mainloop()


