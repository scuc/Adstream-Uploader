#!/usr/bin/env python3

import json
import logging
import os
import time

from datetime import datetime
from pathlib import Path
from time import localtime, strftime

import config as cfg


config = cfg.get_config()
logger = logging.getLogger(__name__)



def get_date(): 

    """
    get todays date and time, use the month value to build a list of log files.
    """

    today = datetime.today()
    year = today.strftime('%Y')
    month = today.strftime('%m')
    day = today.strftime('%d')

    return year, month, day



def job_id_cleanup(): 

    year, month, day = get_date()
    prev_month = int(month) - 1
    
    if len(str(prev_month)) != 2: 
        prev_month = "0"+ str(prev_month)

  