# -*- coding: utf-8 -*-
import logging

logging.basicConfig(level=logging.INFO,
                format='%(asctime)s [%(levelname)s] %(message)s',
                datefmt='%a, %d %b %Y %H:%M:%S')

class AboveInfoFilter(logging.Filter):
        def filter(self, record):
            return record.levelno > 20

def add_file_logging (logger, logfile):
    logfileHndl = logging.FileHandler(logfile)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    logfileHndl.setFormatter(formatter)  
    #logfileHndl.addFilter(AboveInfoFilter())
    logger.addHandler(logfileHndl)

