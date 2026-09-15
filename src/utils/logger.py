import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
import json
from datetime import datetime


class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'name': record.name,
            'message': record.getMessage(),
        }

        if hasattr(record, 'inn'):
            log_data['inn'] = record.inn

        if hasattr(record, 'source'):
            log_data['source'] = record.source

        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


def setup_logger(name: str = 'company_parser', config: dict = None):
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    if config is None:
        config = {}

    log_level = config.get('level', 'INFO')
    log_file = config.get('file', 'logs/app.log')
    max_size_mb = config.get('max_size_mb', 10)
    backup_count = config.get('backup_count', 5)
    format_type = config.get('format', 'json')
    console_output = config.get('console_output', True)

    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL,
    }

    logger.setLevel(level_map.get(log_level, logging.INFO))

    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_size_mb * 1024 * 1024,
        backupCount=backup_count,
    )

    if format_type == 'json':
        file_formatter = JSONFormatter()
    else:
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    return logger


def get_logger(name: str = 'company_parser'):
    return logging.getLogger(name)