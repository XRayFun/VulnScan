import logging
import os

from _conf.base import TEMP_DIR


LOG_OUTPUT_FOLDER = f"{TEMP_DIR}log/"
if not os.path.exists(LOG_OUTPUT_FOLDER):
    os.mkdir(LOG_OUTPUT_FOLDER)

LOG_FORMAT = "[%(asctime)-15s | %(levelname)-8s] %(message)s"

LOG_LEVEL = logging.INFO

MODULE_WIDTH = 26

IP_WIDTH = 18

STATUS_WIDTH = 18
