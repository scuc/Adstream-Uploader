import datetime
import json
import logging
import os
import shutil
import time
from pathlib import Path, PurePosixPath

import requests

import config as cfg
import get_authentication as getauth

# Configuration setup
config = cfg.get_config()
root_folder_id = config["Adstream"]["NatGeoPromoExchange"]
root_fsis3 = Path(config["paths"]["root_fsis3_posix"])
uploaded_rel_path = Path(config["paths"]["upload_dir_posix"])
uploaded_dir_path = Path(root_fsis3, uploaded_rel_path)

logger = logging.getLogger(__name__)


def new_media_creation(adstream_upload_list):
    """
    Handles the complete media upload process to Adstream:
    1. Registers a placeholder for the new media.
    2. Uploads the media.
    3. Completes the media creation.

    Args:
        adstream_upload_list (list of dict): List of media files to upload.

    Returns:
        dict: Summary of the upload process.
    """
    logger.info("Starting media upload to Adstream")
    logger.info(
        f"\n\n=========== AdStream NEW MEDIA LIST ===========:\n{json.dumps(adstream_upload_list, indent=4)}\n"
    )

    media_summary = {"Uploaded Files": [], "Failed Uploads": []}

    for media in adstream_upload_list:
        if not media:
            continue

        time.sleep(10)  # Throttle to avoid overwhelming the server

        vantage_job_id = media["Job Id"]
        registered_media = register_media(media["File Name"], vantage_job_id)

        if registered_media:
            upload_params = prepare_upload_params(media, registered_media)
            media_params = upload_media(vantage_job_id, **upload_params)

            if media_params:
                media_finish = media_complete(
                    vantage_job_id, upload_params["media_path"], **media_params
                )
                if media_finish:
                    media_summary["Uploaded Files"].append(media["File Name"])
                else:
                    media_summary["Failed Uploads"].append(media["File Name"])
            else:
                logger.error(
                    f"Media Upload ERROR for {vantage_job_id}, moving to next upload."
                )
        else:
            logger.error(
                f"Media Registration ERROR for {vantage_job_id}, moving to next."
            )

    return media_summary


def register_media(filename, vantage_job_id):
    """
    Registers a placeholder for new media.

    Args:
        filename (str): Name of the media file.
        vantage_job_id (str): Identifier for the Vantage job.

    Returns:
        dict or None: Response from the registration request or None if an error occurs.
    """
    url = f"https://a5.adstream.com/api/v2/folders/{root_folder_id}/media"
    json_data = {"filename": filename}
    headers = {"Authorization": getauth.get_auth(), "Content-Type": "application/json"}

    try:
        response = requests.post(url, headers=headers, json=json_data).json()
        logger.info(f"MEDIA REGISTER RESPONSE: \n{json.dumps(response, indent=4)}")

        if response[0]["status"] == "succeeded":
            logger.info(f"Register media successful for: {filename}")
            return response
        else:
            logger.error(
                f"Media registration error for {filename}, status = {response[0]['status']}"
            )
            return None

    except Exception as e:
        logger.error(f"Exception during media registration for {filename}: {e}")
        cleanup_media_fail(vantage_job_id, filename)
        return None


def prepare_upload_params(media, registered_media):
    """
    Prepares parameters needed for uploading media.

    Args:
        media (dict): Media metadata.
        registered_media (dict): Response from the media registration request.

    Returns:
        dict: Parameters for the media upload.
    """
    file_info = registered_media[0]
    return {
        "media_path": media["File Path"],
        "fileId": file_info["id"],
        "url": file_info["url"],
        "reference": file_info["reference"],
        "storageId": file_info["storageId"],
        "status": file_info["status"],
        "filename": file_info["filename"],
        "folderId": media["folderId"],
    }


def upload_media(vantage_job_id, **upload_params):
    """
    Uploads the media file to AdStream.

    Args:
        vantage_job_id (str): Identifier for the Vantage job.
        **upload_params: Parameters for the media upload.

    Returns:
        dict or None: Upload parameters or None if an error occurs.
    """
    url = upload_params["url"]
    file_path = upload_params["media_path"]
    filename = upload_params["filename"]

    if isinstance(upload_params["media_path"], PurePosixPath):
        logger.info(
            f"media_path in upload_params is a POSIX: {type(upload_params['media_path'])}"
        )
        upload_params["media_path"] = str(upload_params["media_path"])
    else:
        logger.info(
            f"media_path in upload_params is not a POSIX: {type(upload_params['media_path'])}"
        )

    logger.info(f"Upload Params: {json.dumps(upload_params, indent=4)}")
    logger.info(f"Begin media upload for: {upload_params['filename']}")

    try:
        with open(file_path, "rb") as file:
            data = file.read()
            response = requests.put(url, data=data)
            response.raise_for_status()
            logger.info(f"Upload Response - status: {response.status_code}")
            if response.status_code not in [200, 201, 202]:
                logger.error(f"Media Upload for: {filename} returned an empty response")
                raise Exception
            else:
                logger.info(f"Upload to Adstream complete for: {filename}")
                return upload_params

    except Exception as e:
        logger.error(f"Exception during media upload for {filename}: {e}")
        cleanup_media_fail(vantage_job_id, filename)
        return None


def media_complete(vantage_job_id, filepath, **media_params):
    """
    Completes the media creation process.

    Args:
        vantage_job_id (str): Identifier for the Vantage job.
        filepath (str): Path to the media file.
        **media_params: Parameters for completing the media creation.

    Returns:
        bool: True if the process is successful, False otherwise.
    """
    url = f"https://a5.adstream.com/api/v2/folders/{media_params['folderId']}/media/{media_params['fileId']}"
    json_data = {
        "meta": {"common": {"name": media_params["filename"]}},
        "subtype": "element",
    }
    headers = {"Authorization": getauth.get_auth(), "Content-Type": "application/json"}

    try:
        response = requests.post(url, headers=headers, json=json_data).json()
        logger.info(f"media_compelte() Response: {json.dumps(response, indent=4)}")
        if isinstance(response, dict):
            logger.info(f"Media completion successful for {media_params['filename']}")
            shutil.move(filepath, uploaded_dir_path)
            return True
        else:
            logger.error(
                f"Unexpected response for {media_params['filename']}: \n: {response.text}"
            )
            return False

    except Exception as e:
        logger.error(
            f"Exception during media completion for {media_params['filename']}: {e}"
        )
        cleanup_media_fail(vantage_job_id, media_params["filename"])
        return False


def cleanup_media_fail(vantage_job_id, filename):
    """
    Cleans up job ID list if media creation fails.

    Args:
        vantage_job_id (str): Identifier for the Vantage job.
        filename (str): Name of the media file.
    """
    logger.info(f"Starting Job ID clean up for - {vantage_job_id}")
    job_file = "job_id_list.txt"
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d, %H:%M:%S")

    with open(job_file, "r") as file:
        lines = file.readlines()

    with open(job_file, "w") as file:
        for line in lines:
            if line.strip() == vantage_job_id:
                file.write(
                    f"[ {timestamp} - Upload Failed for job id: {vantage_job_id} ]\n"
                )
                logger.info(
                    f"Adstream Media Creation Failure - Job ID: {vantage_job_id}, Filename: {filename}"
                )
            else:
                file.write(line)


if __name__ == "__main__":
    new_media_creation()
