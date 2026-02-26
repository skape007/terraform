import os
import logging

LOG_LEVEL = os.environ.get('LOG_LEVEL', 'DEBUG').upper()
LOG_FORMAT = '%(asctime)s.%(msecs)03dZ | %(levelname)s | %(message)s'
DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'

def setup_logger():
    logger = logging.getLogger("appLogger")
    logger.setLevel(LOG_LEVEL)
    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)

    # Console handler
    if not logger.handlers:
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)
    else:
        for h in logger.handlers:
            h.setFormatter(formatter)
    return logger

appLogger = setup_logger()

def log_info(message, **kwargs):
    appLogger.info(message, extra=kwargs)

def log_error(message, **kwargs):
    appLogger.error(message, extra=kwargs)

def log_warn(message, **kwargs):
    appLogger.warning(message, extra=kwargs)