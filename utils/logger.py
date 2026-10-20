"""
utils/logger.py
---------------
Structured, timestamped logging for the Elliott Wave bot.
Writes to both console (stdout) and a rotating log file.

Usage:
    from utils.logger import get_logger
    log = get_logger(__name__)
    log.info("Fetched 500 candles for BTC/USDT 1h")
"""

import logging
import os
import queue
import sys
from logging.handlers import RotatingFileHandler, QueueHandler, QueueListener

# [FE1.10.2] عداد إسقاطات طابور التسجيل (نمط flowmap logging_setup.py) —
# تُعرض في /health قسم resilience: امتلاء الطابور يعني إسقاطًا مُعدًّا لا حجبًا.
QUEUE_STATS = {"dropped": 0, "capacity": 2048}


class _BoundedQueueHandler(QueueHandler):
    """QueueHandler بطابور محدود — ازدحام logging يعني إسقاط السجل مُعدًّا
    بدل حجب المسار الساخن (حلقة التداول) على stdout/قرص متعثر. نمط flowmap:
    كل طابور محدود السعة وسياسة الإسقاط معلنة وعدادها مرئي."""

    def enqueue(self, record: logging.LogRecord) -> None:
        try:
            self.queue.put_nowait(record)
        except queue.Full:
            QUEUE_STATS["dropped"] += 1  # إسقاط مُعد — لا يرفع أبدًا للمُنتج


def get_logger(name: str, log_dir: str = "logs", log_file: str = "bot.log",
               level: str = "INFO") -> logging.Logger:
    """
    Return a logger with console + rotating-file handlers (via bounded queue).

    [FE1.10.2] المرسلات (stdout + ملف دوّار) تعمل على خيط QueueListener خلف
    طابور محدود 2048 سجلًا — حجب stdout على المنصة أو بطء القرص لا يجمّد
    حلقة التداول أبدًا، والإسقاطات تُعد وتُعرض في /health.
    """
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers if get_logger is called multiple times
    if logger.handlers:
        return logger

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ── Sink handlers (driven by the listener thread) ──────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(fmt)
    console_handler.setLevel(numeric_level)

    # ── Rotating file handler (10 MB × 5 backups) ─────────────────────────
    file_path = os.path.join(log_dir, log_file)
    file_handler = RotatingFileHandler(
        file_path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(numeric_level)

    # ── Bounded admission queue + listener ────────────────────────────────
    qh = _BoundedQueueHandler(queue.Queue(maxsize=QUEUE_STATS["capacity"]))
    qh.setLevel(numeric_level)
    listener = QueueListener(qh.queue, console_handler, file_handler,
                             respect_handler_level=True)
    listener.start()
    import atexit
    atexit.register(listener.stop)  # إنهاء نظيف — لا خيوط يتيمة عند الإغلاق

    logger.addHandler(qh)
    return logger


# ── Adaptive price formatter ───────────────────────────────────────────────────

def fmt_price(price: float) -> str:
    """
    Format a price with adaptive decimal places based on its magnitude.

    Prevents micro-priced tokens (SHIB, PEPE, etc.) from displaying as
    "0.0000" when formatted with the fixed %.4f specifier used throughout
    the codebase.

    Examples
    --------
    fmt_price(76000.50)      → "76,000.50"
    fmt_price(3456.789)      → "3,456.7890"
    fmt_price(0.003456)      → "0.003456"
    fmt_price(0.0000043456)  → "0.00000435"
    fmt_price(0.0000000012)  → "1.2400e-09"
    """
    if price == 0:
        return "0.0"
    abs_p = abs(price)
    if abs_p >= 1_000:
        return f"{price:,.2f}"
    elif abs_p >= 1:
        return f"{price:.4f}"
    elif abs_p >= 0.001:
        return f"{price:.6f}"
    elif abs_p >= 0.000_001:
        return f"{price:.8f}"
    else:
        return f"{price:.4e}"
