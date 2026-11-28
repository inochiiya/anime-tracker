import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


class SafeRotatingFileHandler(RotatingFileHandler):
    """Create the log directory before opening a rotating log file."""

    def __init__(self, filename, *args, **kwargs):
        Path(filename).resolve().parent.mkdir(parents=True, exist_ok=True)
        super().__init__(filename, *args, **kwargs)


class AccessLogFilter(logging.Filter):
    """Keep access logs compact and promote HTTP failures to useful levels."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not isinstance(record.args, tuple) or len(record.args) != 5:
            return True

        client_addr, method, path, http_version, status_code = record.args
        client_addr = str(client_addr)
        if client_addr.endswith(":0"):
            client_addr = client_addr[:-2]
        if str(path).startswith("/api/proxy/cover?"):
            path = "/api/proxy/cover"

        status_code = int(status_code)
        if status_code >= 500:
            record.levelno = logging.ERROR
            record.levelname = "ERROR"
        elif status_code >= 400:
            record.levelno = logging.WARNING
            record.levelname = "WARNING"

        record.args = (client_addr, method, path, http_version, status_code)
        return True
