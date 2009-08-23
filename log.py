# -*- coding: utf-8 -*-
import logging, logging.handlers  
from django.conf import settings  
  
LOGGING_INITIATED = False  
  
def init_logging():  
    logger = logging.getLogger('project_logger')
    if settings.LOG_LEVEL == "DEBUG":
      logging.basicConfig(filename=settings.LOG_FILE,level=logging.DEBUG)
    else:
      logging.basicConfig(filename=settings.LOG_FILE,level=logging.INFO)
  
    #handler = logging.handlers.TimedRotatingFileHandler(settings.LOG_FILENAME, when = 'midnight')  
    #formatter = logging.Formatter(LOG_MSG_FORMAT)  
    #handler.setFormatter(formatter)  
    #logger.addHandler(handler)  
  
if not LOGGING_INITIATED:  
    LOGGING_INITIATED = True  
    init_logging()  