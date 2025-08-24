import tkinter as tk
from tkinter import ttk
import ctypes
from ctypes import wintypes
import logging
import psutil


# Настройка логирования (краткие русские сообщения)
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Загрузка библиотек WinAPI
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
psapi = ctypes.WinDLL('psapi', use_last_error=True)



# Константы WinAPI
IDLE_PRIORITY_CLASS = 0x40
BELOW_NORMAL_PRIORITY_CLASS = 0x4000
NORMAL_PRIORITY_CLASS = 0x20
ABOVE_NORMAL_PRIORITY_CLASS = 0x8000
HIGH_PRIORITY_CLASS = 0x80
REALTIME_PRIORITY_CLASS = 0x100
THREAD_SUSPEND_RESUME = 0x0002

# Минимальный набор флагов (замена win32con для линтера)
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
PROCESS_TERMINATE = 0x0001
PROCESS_SET_INFORMATION = 0x0200
CREATE_NEW_CONSOLE = 0x00000010



# Определение структур
class STARTUPINFO(ctypes.Structure):
    _fields_ = [
        ('cb', wintypes.DWORD), ('lpReserved', wintypes.LPWSTR), ('lpDesktop', wintypes.LPWSTR),
        ('lpTitle', wintypes.LPWSTR), ('dwX', wintypes.DWORD), ('dwY', wintypes.DWORD),
        ('dwXSize', wintypes.DWORD), ('dwYSize', wintypes.DWORD), ('dwXCountChars', wintypes.DWORD),
        ('dwYCountChars', wintypes.DWORD), ('dwFillAttribute', wintypes.DWORD), ('dwFlags', wintypes.DWORD),
        ('wShowWindow', wintypes.WORD), ('cbReserved2', wintypes.WORD), ('lpReserved2', wintypes.LPBYTE),
        ('hStdInput', wintypes.HANDLE), ('hStdOutput', wintypes.HANDLE), ('hStdError', wintypes.HANDLE),
    ]

class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ('hProcess', wintypes.HANDLE), ('hThread', wintypes.HANDLE),
        ('dwProcessId', wintypes.DWORD), ('dwThreadId', wintypes.DWORD),
    ]

class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    # Структура счётчиков памяти процесса
    _fields_ = [
        ('cb', wintypes.DWORD),
        ('PageFaultCount', wintypes.DWORD),
        ('PeakWorkingSetSize', ctypes.c_size_t),
        ('WorkingSetSize', ctypes.c_size_t),
        ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
        ('QuotaPagedPoolUsage', ctypes.c_size_t),
        ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
        ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
        ('PagefileUsage', ctypes.c_size_t),
        ('PeakPagefileUsage', ctypes.c_size_t),
    ]



# Функции
def get_process_memory(pid):
    """Возврат рабочего набора процесса в КБ или "Н/Д"."""
    handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not handle:
        return "Н/Д"
    mem_info = PROCESS_MEMORY_COUNTERS()
    mem_info.cb = ctypes.sizeof(mem_info)
    ok = psapi.GetProcessMemoryInfo(handle, ctypes.byref(mem_info), ctypes.sizeof(mem_info))
    kernel32.CloseHandle(handle)
    if ok:
        return int(mem_info.WorkingSetSize // 1024)
    return "Н/Д"

def get_thread_handles(pid):
    """Открытие потоков процесса с правами приостановки/возобновления."""
    try:
        proc = psutil.Process(pid)
        threads = proc.threads()
        if not threads:
            return []
        thread_handles = []
        for thread in threads:
            thread_handle = kernel32.OpenThread(THREAD_SUSPEND_RESUME, False, thread.id)
            if thread_handle:
                thread_handles.append(thread_handle)
        return thread_handles
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return []

def get_thread_count(pid):
    try:
        proc = psutil.Process(pid)
        return len(proc.threads())
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return 0

def get_process_tree():
    process_dict = {}
    # Простой опрос всех PID
    for pid in psutil.pids():
        try:
            p = psutil.Process(pid)
            process_dict[pid] = {
                'name': p.name(),
                'pid': pid,
                'ppid': p.ppid() or 0,
                'children': [],
                'status': "Running"
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    # Строим дерево
    tree = {}
    for pid, info in process_dict.items():
        ppid = info['ppid']
        if ppid in process_dict:
            process_dict[ppid]['children'].append(pid)
        else:
            tree[pid] = info
    return tree, process_dict

class ProcessManagerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Process Manager")
        self.geometry("800x600")

        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.process_tree = ttk.Treeview(self.main_frame, columns=("PID", "Memory", "Threads", "Priority", "Status"))
        self.process_tree.heading("#0", text="Process")
        self.process_tree.heading("PID", text="PID")
        self.process_tree.heading("Memory", text="Memory (KB)")
        self.process_tree.heading("Threads", text="Threads")
        self.process_tree.heading("Priority", text="Priority")
        self.process_tree.heading("Status", text="Status")
        self.process_tree.column("#0", width=200)
        self.process_tree.column("PID", width=80)
        self.process_tree.column("Memory", width=100)
        self.process_tree.column("Threads", width=80)
        self.process_tree.column("Priority", width=100)
        self.process_tree.column("Status", width=100)
        self.process_tree.pack(fill=tk.BOTH, expand=True)

        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.pack(fill=tk.X, pady=5)

        # Priority selection for change priority
        self.priority_var = tk.StringVar(value="Normal")
        priorities = ["Idle", "Below normal", "Normal", "Above normal", "High", "Realtime"]
        ttk.Label(self.button_frame, text="Priority:").pack(side=tk.LEFT, padx=5)
        ttk.OptionMenu(self.button_frame, self.priority_var, "Normal", *priorities).pack(side=tk.LEFT, padx=5)

        ttk.Button(self.button_frame, text="Create", command=self.create_process).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.button_frame, text="Terminate", command=self.terminate_process).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.button_frame, text="Terminate tree", command=self.terminate_tree).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.button_frame, text="Change priority", command=self.change_priority).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.button_frame, text="Suspend/Resume", command=self.suspend_resume_thread).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.button_frame, text="Refresh", command=self.update_process_list).pack(side=tk.LEFT, padx=5)

        # Локальный статус потоков по PID
        self.thread_status = {}
        # Инициализация списка при запуске
        self.update_process_list()

    def update_process_list(self):
        self.process_tree.delete(*self.process_tree.get_children())
        tree, process_dict = get_process_tree()

        def insert_process(pid, parent=""):
            if pid not in process_dict:
                return
            proc_info = process_dict[pid]
            memory = get_process_memory(pid)
            threads = get_thread_count(pid)
            handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION, False, pid)
            priority = kernel32.GetPriorityClass(handle) if handle else 0
            kernel32.CloseHandle(handle) if handle else None
            priority_map = {
                HIGH_PRIORITY_CLASS: "High",
                ABOVE_NORMAL_PRIORITY_CLASS: "Above normal",
                NORMAL_PRIORITY_CLASS: "Normal",
                BELOW_NORMAL_PRIORITY_CLASS: "Below normal",
                IDLE_PRIORITY_CLASS: "Idle",
                REALTIME_PRIORITY_CLASS: "Realtime"
            }
            priority_str = priority_map.get(priority, str(priority))
            status = self.thread_status.get(pid, proc_info['status'])
            item = self.process_tree.insert(
                parent, "end", text=proc_info['name'], values=(pid, memory, threads, priority_str, status)
            )
            for child_pid in sorted(proc_info['children']):
                insert_process(child_pid, item)

        for pid in sorted(tree.keys()):
            insert_process(pid)

    def create_process(self):
        # Создает notepad, процесс будет дочерним по отношению к Python/IDE
        try:
            si = STARTUPINFO()
            si.cb = ctypes.sizeof(STARTUPINFO)
            pi = PROCESS_INFORMATION()
            cmd = "notepad.exe"
            creation_flags = CREATE_NEW_CONSOLE
            ok = kernel32.CreateProcessW(
                None, cmd, None, None, False,
                creation_flags, None, None, ctypes.byref(si), ctypes.byref(pi)
            )
            if not ok:
                raise ctypes.WinError(ctypes.get_last_error())
            kernel32.CloseHandle(pi.hProcess)
            kernel32.CloseHandle(pi.hThread)
        except Exception as e:
            logger.error(f"Не удалось создать процесс: {e}")

    def terminate_process(self):
        selected_item = self.process_tree.selection()
        if not selected_item:
            logger.error("Процесс не выбран")
            return
        pid = int(self.process_tree.item(selected_item, "values")[0])
        try:
            h_process = kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
            if h_process:
                kernel32.TerminateProcess(h_process, 1)
                kernel32.CloseHandle(h_process)
            else:
                logger.error("Не удалось открыть процесс")
            if pid in self.thread_status:
                del self.thread_status[pid]
        except Exception as e:
            logger.error(f"Не удалось завершить процесс: {e}")

    def terminate_tree(self):
        """Завершение процесса и всех его потомков."""
        selected_item = self.process_tree.selection()
        if not selected_item:
            logger.error("Процесс не выбран")
            return
        pid = int(self.process_tree.item(selected_item, "values")[0])
        try:
            proc = psutil.Process(pid)
            children = proc.children(recursive=True)
            for ch in children:
                try:
                    h = kernel32.OpenProcess(PROCESS_TERMINATE, False, ch.pid)
                    if h:
                        kernel32.TerminateProcess(h, 1)
                        kernel32.CloseHandle(h)
                except Exception:
                    pass
            h_parent = kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
            if h_parent:
                kernel32.TerminateProcess(h_parent, 1)
                kernel32.CloseHandle(h_parent)
            else:
                logger.error("Не удалось открыть процесс")
            for ch in children:
                self.thread_status.pop(ch.pid, None)
            self.thread_status.pop(pid, None)
        except psutil.NoSuchProcess:
            logger.error("Процесс больше не существует")
        except Exception as e:
            logger.error(f"Не удалось завершить дерево: {e}")

    def change_priority(self):
        selected_item = self.process_tree.selection()
        if not selected_item:
            logger.error("Процесс не выбран")
            return
        pid = int(self.process_tree.item(selected_item, "values")[0])
        priority_map = {
            "Idle": IDLE_PRIORITY_CLASS,
            "Below normal": BELOW_NORMAL_PRIORITY_CLASS,
            "Normal": NORMAL_PRIORITY_CLASS,
            "Above normal": ABOVE_NORMAL_PRIORITY_CLASS,
            "High": HIGH_PRIORITY_CLASS,
            "Realtime": REALTIME_PRIORITY_CLASS
        }
        priority = priority_map.get(self.priority_var.get(), NORMAL_PRIORITY_CLASS)
        try:
            h_process = kernel32.OpenProcess(PROCESS_SET_INFORMATION, False, pid)
            if h_process:
                kernel32.SetPriorityClass(h_process, priority)
                kernel32.CloseHandle(h_process)
            else:
                logger.error("Не удалось открыть процесс")
        except Exception as e:
            logger.error(f"Не удалось изменить приоритет: {e}")

    def suspend_resume_thread(self):
        selected_item = self.process_tree.selection()
        if not selected_item:
            logger.error("Процесс не выбран")
            return
        pid = int(self.process_tree.item(selected_item, "values")[0])
        try:
            thread_handles = get_thread_handles(pid)
            if not thread_handles:
                logger.error("Не найдено доступных потоков для этого процесса")
                return

            current_status = self.thread_status.get(pid, "Running")
            if current_status == "Running":
                for handle in thread_handles:
                    result = kernel32.SuspendThread(handle)
                    if result == -1:
                        error = ctypes.get_last_error()
                        logger.error(f"Не удалось приостановить поток: {error}")
                        break
                else:
                    self.thread_status[pid] = "Suspended"
            else:
                for handle in thread_handles:
                    result = kernel32.ResumeThread(handle)
                    if result == -1:
                        error = ctypes.get_last_error()
                        logger.error(f"Не удалось возобновить поток: {error}")
                        break
                else:
                    self.thread_status[pid] = "Running"

            for handle in thread_handles:
                kernel32.CloseHandle(handle)
        except psutil.NoSuchProcess:
            logger.error("Процесс больше не существует")
        except Exception as e:
            logger.error(f"Не удалось приостановить/возобновить потоки: {e}")


if __name__ == "__main__":
    app = ProcessManagerApp()
    app.mainloop()