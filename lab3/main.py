import time
import threading
import random
import csv
import ctypes
from ctypes import wintypes


# Константы 
SEED = 42
CHAIRS = 3
BURST_SIZE = 12
HAIRCUT_MS_RANGE = (200, 400)
FIB_N = 35
HOLD_LOCK_MS = 300  # задержка лока, мс
ENABLE_THREAD_SAFETY = True  # False — отключает локи (для демонстрации гонок)

# WinAPI (ctypes)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
WAIT_OBJECT_0 = 0x00000000
INFINITE = 0xFFFFFFFF


class WinMutex:
    def __init__(self):
        self.handle = kernel32.CreateMutexW(None, False, None)

    def acquire(self, timeout_ms=None) -> bool:
        ms = INFINITE if (timeout_ms is None) else int(timeout_ms)
        res = kernel32.WaitForSingleObject(self.handle, ms)
        return res == WAIT_OBJECT_0

    def release(self) -> None:
        kernel32.ReleaseMutex(self.handle)

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *args):
        self.release()


class WinSemaphore:
    def __init__(self, initial: int = 0, maximum: int = 0x7fffffff):
        self.handle = kernel32.CreateSemaphoreW(None, initial, maximum, None)

    def acquire(self, timeout_s: float | None = None) -> bool:
        ms = INFINITE if (timeout_s is None) else int(timeout_s * 1000)
        res = kernel32.WaitForSingleObject(self.handle, ms)
        return res == WAIT_OBJECT_0

    def release(self, count: int = 1) -> None:
        kernel32.ReleaseSemaphore(self.handle, count, None)


class WinEvent:
    def __init__(self, manual_reset: bool = False, initial_state: bool = False):
        self.handle = kernel32.CreateEventW(None, bool(manual_reset), bool(initial_state), None)

    def set(self) -> None:
        kernel32.SetEvent(self.handle)

    def reset(self) -> None:
        kernel32.ResetEvent(self.handle)

    def wait(self, timeout_s: float | None = None) -> bool:
        ms = INFINITE if (timeout_s is None) else int(timeout_s * 1000)
        res = kernel32.WaitForSingleObject(self.handle, ms)
        return res == WAIT_OBJECT_0

    def is_set(self) -> bool:
        return self.wait(0)


class WinBarrier:
    """Одноразовый барьер на WinAPI (manual-reset event)."""
    def __init__(self, parties: int):
        self.parties = parties
        self.count = 0
        self.lock = WinMutex()
        self.evt = WinEvent(manual_reset=True, initial_state=False)

    def wait(self):
        with self.lock:
            self.count += 1
            if self.count >= self.parties:
                self.evt.set()
        self.evt.wait()


class _NullLock:
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False

class BarberShop:
    def __init__(self, csv_path: str):
        self.queue = []
        self.state_lock = WinMutex() if ENABLE_THREAD_SAFETY else _NullLock()
        self.customers = WinSemaphore(0)
        self.stop = WinEvent()
        self.arrived = 0
        self.served = 0
        self.lost = 0
        self.barber_thr = None
        self.log_lock = WinMutex()
        self.csv_file = open(csv_path, "w", newline="", encoding="utf-8")
        self.csv = csv.writer(self.csv_file)
        self.csv.writerow(["ts", "perf_ns", "thread", "client", "event", "q_len", "free"])
        self.csv_file.flush()

    def _fib(self, n: int) -> int:
        if n <= 1:
            return n
        return self._fib(n - 1) + self._fib(n - 2)

    def _log(self, ev: str, cid=None, q_len=None, free=None):
        if q_len is None or free is None:
            with self.state_lock:
                q_len = len(self.queue)
                free = CHAIRS - q_len
        now = time.time()
        ts_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now)) + f".{int((now % 1)*1000):03d}"
        pn = time.perf_counter_ns()
        with self.log_lock:
            self.csv.writerow([ts_str, str(pn), str(threading.get_ident()), cid, ev, q_len, free])
            self.csv_file.flush()
            # дублируем в консоль
            print(f"{ts_str} thr={threading.get_ident()} client={cid} {ev} q_len={q_len} free={free}")

    def start_barber(self):
        def loop():
            while not self.stop.is_set():
                if not self.customers.acquire(timeout_s=0.1):
                    continue
                with self.state_lock:
                    if HOLD_LOCK_MS > 0:
                        time.sleep(HOLD_LOCK_MS / 1000.0)
                    token = self.queue.pop(0) if self.queue else None
                if token is None:
                    continue
                cid = token['id']
                try:
                    self._fib(FIB_N)
                except RecursionError:
                    pass
                time.sleep(random.randint(*HAIRCUT_MS_RANGE) / 1000.0)
                token['ev'].set()
                with self.state_lock:
                    self.served += 1
                
        self.barber_thr = threading.Thread(target=loop, name="Barber", daemon=True)
        self.barber_thr.start()

    def spawn_client(self, cid: int, barrier: WinBarrier):
        def run():
            barrier.wait()
            with self.state_lock:
                self.arrived += 1
                ql = len(self.queue)
                fr = CHAIRS - ql
            self._log("arrive", cid, q_len=ql, free=fr)
            token = {'id': cid, 'ev': WinEvent()}
            with self.state_lock:
                if HOLD_LOCK_MS > 0:
                    time.sleep(HOLD_LOCK_MS / 1000.0)
                if len(self.queue) < CHAIRS:
                    self.queue.append(token)
                    ql = len(self.queue)
                    fr = CHAIRS - ql
                    queued = True
                else:
                    ql = len(self.queue)
                    fr = CHAIRS - ql
                    queued = False
            if queued:
                self._log("seat_taken", cid, q_len=ql, free=fr)
                self.customers.release()
                token['ev'].wait()
                self._log("served", cid)
            else:
                with self.state_lock:
                    self.lost += 1
                    ql = len(self.queue)
                    fr = CHAIRS - ql
                self._log("queue_full", cid, q_len=ql, free=fr)
        t = threading.Thread(target=run, name=f"Client-{cid}")
        t.start()
        return t

    def shutdown(self):
        self.stop.set()
        self.customers.release()
        if self.barber_thr:
            self.barber_thr.join(timeout=5)
        with self.log_lock:
            try:
                self.csv_file.flush()
                self.csv_file.close()
            except Exception:
                pass

    def summary(self):
        with self.state_lock:
            a, s, l = self.arrived, self.served, self.lost
            q_len = len(self.queue)
            free = CHAIRS - q_len
        print(f"SUMMARY: arrived={a} served={s} lost={l} q_len={q_len} free={free}")

    def assert_invariants(self):
        with self.state_lock:
            q_len = len(self.queue)
            assert 0 <= q_len <= CHAIRS, "queue length bounds broken"
            assert self.arrived >= self.served + self.lost, "arrivals accounting broken"


def run_burst():
    random.seed(SEED)
    
    ts_name = time.strftime("%Y%m%d_%H%M%S") + f"_{int((time.time()%1)*1000):03d}.csv"
    csv_path = ts_name
    shop = BarberShop(csv_path)
    shop.start_barber()
    barrier = WinBarrier(BURST_SIZE + 1)
    threads = [shop.spawn_client(i + 1, barrier) for i in range(BURST_SIZE)]
    start_t = None
    barrier.wait()
    start_t = time.perf_counter()
    for t in threads:
        t.join()
    time.sleep(0.2)
    end_t = time.perf_counter()
    shop.shutdown()
    # summary
    with shop.state_lock:
        a = shop.arrived
        s = shop.served
        l = shop.lost
        q_len = len(shop.queue)
        free = CHAIRS - q_len
    dur_ms = int(((end_t - (start_t or end_t)) * 1000))
    print(f"arrived={a} served={s} lost={l} q_len={q_len} free={free} duration_ms={dur_ms}")
    print(csv_path)


if __name__ == "__main__":
    run_burst()


