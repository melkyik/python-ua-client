import os
import logging
from logging.handlers import RotatingFileHandler
from uvicorn.logging import UvicornLogger
import inspect
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# mylogger = logging.getLogger(module_name)
# logging.getLogger(__name__)
# mylogger.setLevel(logging.INFO)  # Set the log level for the custom logger

file_handler = RotatingFileHandler("/var/scripts/python-ua-client/logs/mixings.log", maxBytes=100000, backupCount=10,encoding="UTF8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)


def init_handlers():
    
    logging.basicConfig(level=logging.INFO,
                        format="%(name)s - %(levelname)s - %(message)s",
                        datefmt=  '%Y-%m-%d %H:%M:%S')  
    logging.getLogger("FarmClass").addHandler(file_handler)
    logging.getLogger("fastapi").addHandler(file_handler)
 

    logging.getLogger("fastapi").addHandler(console_handler)
    logging.getLogger("uvicorn").addHandler(console_handler)

# Clear any existing handlers to avoid duplicated logs
#mylogger.handlers.clear()

#mylogger.addHandler(file_handler)
#mylogger.addHandler(console_handler)

# Disable propagation to prevent log records from being passed up to the root logger
#mylogger.propagate = False