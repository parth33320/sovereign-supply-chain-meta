import logging
import json
import sys
from datetime import datetime, UTC

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage()
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)

def setup_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root_logger = logging.getLogger()
    if not any(isinstance(h, logging.StreamHandler) and isinstance(h.formatter, JSONFormatter) for h in root_logger.handlers):
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)
