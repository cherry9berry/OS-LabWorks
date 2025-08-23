import time
import threading
import random
import csv


# Константы 
SEED = 42
CHAIRS = 3
BURST_SIZE = 12
HAIRCUT_MS_RANGE = (200, 400)
FIB_N = 35
HOLD_LOCK_MS = 300  # задержка лока, мс
ENABLE_THREAD_SAFETY = True  # False — отключает локи (для демонстрации гонок)


class _NullLock:
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False

class BarberShop:
    def __init__(self, csv_path: str):
        self.queue = []
        self.state_lock = threading.Lock() if ENABLE_THREAD_SAFETY else _NullLock()
        self.customers = threading.Semaphore(0)
        self.stop = threading.Event()
        self.arrived = 0
        self.served = 0
        self.lost = 0
        self.barber_thr = None
        self.log_lock = threading.Lock()
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
                if not self.customers.acquire(timeout=0.1):
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

    def spawn_client(self, cid: int, barrier: threading.Barrier):
        def run():
            try:
                barrier.wait()
            except threading.BrokenBarrierError:
                pass
            with self.state_lock:
                self.arrived += 1
                ql = len(self.queue)
                fr = CHAIRS - ql
            self._log("arrive", cid, q_len=ql, free=fr)
            token = {'id': cid, 'ev': threading.Event()}
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
        try:
            self.customers.release()
        except ValueError:
            pass
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
    barrier = threading.Barrier(BURST_SIZE + 1)
    threads = [shop.spawn_client(i + 1, barrier) for i in range(BURST_SIZE)]
    start_t = None
    try:
        barrier.wait()
        start_t = time.perf_counter()
    except threading.BrokenBarrierError:
        pass
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


