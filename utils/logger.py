"""
Markazlashtirilgan logging konfiguratsiyasi.
Barcha modullar shu fayldan logger oladi.
"""
import logging
import sys
from logging.handlers import RotatingFileHandler


def setup_logging(level: int = logging.INFO) -> None:
    """
    Ilovani ishga tushirishda bir marta chaqiriladi.
    Konsolga va faylga (rotating) yozadi.
    """
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    # Asosiy format
    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

    # Konsol handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    # Fayl handler (max 5 MB, 3 ta backup)
    file_handler = RotatingFileHandler(
        filename="bot.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Keraksiz kutubxona loglarini susaytirish
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Modul nomi bilan logger qaytaradi."""
    return logging.getLogger(name)
