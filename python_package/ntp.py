import time, threading
from datetime import datetime, timedelta
import ntplib
from .config import NTP_SERVERS

offset = 0.0
lock = threading.Lock()

def update():
    global offset
    while True:
        time.sleep(60)
        try:
            t1 = ntplib.NTPClient().request(NTP_SERVERS[0], version=3, timeout=2).tx_time
            t2 = ntplib.NTPClient().request(NTP_SERVERS[1], version=3, timeout=2).tx_time
            t = t1 if abs(t1-t2)<1 else t2
            with lock: offset = (datetime.utcfromtimestamp(t)+timedelta(hours=8) - datetime.now()).total_seconds()
        except: pass

def ntp_time():
    with lock: return datetime.now() + timedelta(seconds=offset)

threading.Thread(target=update, daemon=True).start()