
import datetime
import glob
import json
import logging
import logging.config
import os
import yaml

from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from time import localtime, strftime

import api_adstream as api_a
import api_vantage as api_v
import get_authentication as getauth

import config as cfg

logger = logging.getLogger(__name__)

config = cfg.get_config()
# source_path = config['paths']['source_path']
# cfg.ensure_dirs(source_path)


def set_logger():
    """
    Setup logging configuration
    """
    path = 'logging.yaml'

    with open(path, 'rt') as f:
        config = yaml.safe_load(f.read())

    # get the file name from the handlers, append the date to the filename. 
        for i in (config["handlers"].keys()):
            if 'filename' in config['handlers'][i]:
                log_filename = config["handlers"][i]["filename"]
                base, extension = os.path.splitext(log_filename)
                today = datetime.datetime.today()
                log_filename = "{}_{}{}".format(base,
                                                today.strftime("%Y%m%d"),
                                                extension)
                config["handlers"][i]["filename"] = log_filename
            else:
                print("+++++++++++++++ LOG FILE ERROR ++++++++++++++++")

        logger = logging.config.dictConfig(config)

    return logger



def main(): 
    """
    This script talk to the Vantage REST api to look for new jobs in a specific workflow. 
    If new jobs are found, they are added to a list of dicts with the job variables - jobid, filename, filepath. 
    The script then loops over the job list - for each job it talks to the Adstream API. 
    Three steps to the Adstream API - 
    1) POST - Register new media; 
    2) PUT - Upload the new media; 
    3) POST - Complete the new media creation
    """

    date_start = str(strftime('%A, %d. %B %Y %I:%M%p', localtime()))

    start_msg = f"\n\
    ==================================================================================\n\
                AdStream Upload - Start - {date_start} \n\
    ==================================================================================\n\
   "

    logger.info(start_msg)

    workflow = config["vantage"]["workflow_list"]["_Info for AdStream Uploads"]

    adstream_upload_list = api_v.check_workflows(workflow)

    if len(adstream_upload_list) != 0: 

        api_a.new_media_creation(adstream_upload_list)
        complete_msg()
    
    else: 
        complete_msg()


    
def complete_msg():

    date_end = str(strftime('%A, %d. %B %Y %I:%M%p', localtime()))

    complete_msg = f"\n\
    ================================================================================\n\
                Adstream Upload - Complete - {date_end} \n\
    ================================================================================\n\
    "
    logger.info(complete_msg)

    return
    

    # api_a.get_project(projectId)
    # api_a.get_projects()
    # api_a.get_folder(folderId)
    # api_a.register_media()
    # api_a.search_files()
    # api_a.get_folders()
    # api_a.upload_media(auth)
    # api_a.create_project_folder(auth)


if __name__ == '__main__':
    set_logger()
    main()
