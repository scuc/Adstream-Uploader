import datetime
import logging
import logging.config
import os
from time import localtime, strftime

import yaml

import api_adstream as api_a
import api_vantage as api_v
import config as cfg

logger = logging.getLogger(__name__)


# def load_config():
#     """
#     Load configuration settings.
#     """
#     return cfg.get_config()


def set_logger(script_root):
    """
    Set up logging configuration.
    """
    log_config_path = os.path.join(script_root, "logging.yaml")

    with open(log_config_path, "rt") as f:
        log_config = yaml.safe_load(f.read())

        # Update the log filename with the current date.
        today = datetime.datetime.today().strftime("%Y%m%d")
        for handler in log_config["handlers"].values():
            if "filename" in handler:
                base, extension = os.path.splitext(handler["filename"])
                handler["filename"] = f"{base}_{today}{extension}"

        logging.config.dictConfig(log_config)


def log_start():
    """
    Log the start of the AdStream upload process.
    """
    date_start = strftime("%A, %d. %B %Y %I:%M%p", localtime())
    start_msg = (
        "\n"
        "==================================================================================\n"
        f"            AdStream Upload - Start - {date_start} \n"
        "==================================================================================\n"
    )
    logger.info(start_msg)


def log_complete(media_summary):
    """
    Log the completion of the AdStream upload process.
    """
    date_end = strftime("%A, %d. %B %Y %I:%M%p", localtime())
    uploaded_files = media_summary.get("Uploaded Files", ["None"])
    failed_uploads = media_summary.get("Failed Uploads", ["None"])

    complete_msg = (
        "\n"
        "================================================================================\n"
        f"            AdStream Upload - Complete - {date_end} \n"
        "================================================================================\n"
        f"        Media Uploaded to Adstream: {uploaded_files}\n"
        f"        Media Failed to Upload: {failed_uploads}\n"
        "================================================================================\n"
    )
    logger.info(complete_msg)


def main():
    """
    Main function to handle AdStream uploads.

    This script interacts with the Vantage REST API to identify new jobs within a specific workflow. When new jobs are detected, they are collected into a list of dictionaries, each containing key job details such as jobid, filename, and filepath.

    The script then processes each job in the list by communicating with the Adstream API.
    This involves a three-step process:

    POST - Register new media: Initiates the media registration process with Adstream.
    PUT - Upload the new media: Uploads the media file to Adstream.
    POST - Complete the new media creation: Finalizes the media creation process in Adstream.

    """
    config = cfg.get_config()
    script_root = config["paths"]["script_root"]
    set_logger(script_root)

    log_start()

    workflow = config["vantage"]["workflows"]["_Info for AdStream Uploads"]
    adstream_upload_list = api_v.check_workflows(workflow)

    if adstream_upload_list:
        media_summary = api_a.new_media_creation(adstream_upload_list)
    else:
        media_summary = {
            "Uploaded Files": ["None"],
            "Failed Uploads": ["None"],
        }

    log_complete(media_summary)


if __name__ == "__main__":
    main()
