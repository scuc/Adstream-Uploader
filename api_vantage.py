import json
import logging
import os
import re
from pathlib import PurePosixPath, PureWindowsPath
from sys import platform

import requests

import config as cfg

# Configuration and Logger Setup
config = cfg.get_config()
logger = logging.getLogger(__name__)

adstream_folders = config["Adstream"]
endpoint_list = config["vantage"]["endpoint_list"]
root_unc = config["paths"]["root_unc"]
root_quan2_posix = config["paths"]["root_quan2_posix"]
root_fsis3_posix = config["paths"]["root_fsis3_posix"]
script_root = config["paths"]["script_root"]
workflow = config["vantage"]["workflows"]["_Info for AdStream Uploads"]


def check_workflows(workflow):
    """
    Vantage REST API calls to check workflows for new media and pull variables from jobs.
    """
    api_endpoint = get_endpoint()
    root_uri = f"http://{api_endpoint}:8676/"
    workflow_endpoint = f"{root_uri}/Rest/workflows/{workflow}/jobs"

    response = requests.get(workflow_endpoint).json()
    jobs_list = response.get("Jobs", [])

    logger.info(f"Jobs in the workflow: \n{json.dumps(response, indent=4)}")
    logger.info("Checking Vantage jobs")

    adstream_upload_list = []
    duplicate_count = 0

    for job in jobs_list:
        if job["Name"] == "_Info for AdStream Uploads":
            continue

        job_id = check_jobs(job)
        logger.debug(f"Checking Vantage job: {job_id}")

        if job_id:
            kv_dict = get_job_variables(job_id)
            if kv_dict:
                media_dict = create_media_dict(kv_dict)
                adstream_upload_list.append(media_dict)
            else:
                continue
        else:
            duplicate_count += 1
            logger.debug(f"Job ID: {job['Identifier']} is a duplicate, skipping")

    logger.info("Vantage job check complete.")
    logger.info(f"Total duplicate jobs skipped = {duplicate_count}")

    return adstream_upload_list


def check_jobs(job):
    """
    Check job ID against a list of previously processed jobs.
    """
    job_id = job["Identifier"]
    job_state = job["State"]

    if job_state != 5:
        return None

    logger.debug(f"Checking job: {job_id}, state: {job_state}")

    os.chdir(script_root)
    job_id_list_path = "job_id_list.txt"

    with open(job_id_list_path, "a+") as f:
        f.seek(0)
        contents = f.read()
        failed_job_text = f"Upload Failed for job id: {job_id}"

        if re.search(job_id, contents) and not re.search(failed_job_text, contents):
            logger.info(
                "Job Identifier already exists in the job list, setting job_id to None"
            )
            return None
        else:
            logger.info(
                "Job Identifier does not exist in the job list, returning id for processing."
            )
            return job_id


def get_job_variables(job_id):
    """
    Get the job variables from the Vantage workflow.
    """
    api_endpoint = get_endpoint()
    root_uri = f"http://{api_endpoint}:8676/"
    output_endpoint = f"{root_uri}/Rest/jobs/{job_id}/outputs"

    response = requests.get(output_endpoint).json()
    labels = response.get("Labels", [])

    if labels:
        vars = labels[0].get("Params", [])
        kv_dict = {"Job Id": job_id}
        for var in vars:
            kv_dict[var["Name"]] = var["Value"]

        logger.info(f"Variables for Job ID {job_id}: {kv_dict}")
        return kv_dict
    else:
        logger.info(f"Variables for Job ID {job_id} are empty, returning empty dict")
        return {}


def create_media_dict(kv_dict):
    """
    Use the media upload list to create a list of dicts with key-value pair info needed for upload to Adstream.
    """
    media_dict = {}
    job_id = kv_dict["Job Id"]
    path = kv_dict["File Path"]

    if str(path).startswith("T:\\"):
        path = str(path).replace("T:\\", "").replace("\\", "/")
        path = PurePosixPath(root_quan2_posix, path)
    elif str(path).startswith("\\\\fsis3-smb\\fsis3\\"):
        path = (
            str(path)
            .replace("\\\\fsis3-smb\\fsis3\\", root_fsis3_posix)
            .replace("\\", "/")
        )
        path = PurePosixPath(root_fsis3_posix, path)

    print(f"PATH:  {str(path)}")
    folder = str(path).rsplit("/")[-2]

    logger.info(f"Adstream folder: {folder}\n")

    if folder != "_DeployToAdStream":
        folderId = adstream_folders[folder]
        filename = kv_dict["File Name"]

        if platform == "darwin":
            posix_path = PurePosixPath(path)

        media_dict.update(
            {
                "Job Id": job_id,
                "folderId": folderId,
                "File Name": filename,
                "File Path": posix_path,
            }
        )

    if isinstance(media_dict["File Path"], PurePosixPath):
        logger.info(
            f"'File Path' in media_dict is a POSIX: {type(media_dict['File Path'])}"
        )
        media_dict["File Path"] = str(media_dict["File Path"])
    else:
        logger.info(
            f"'File Path' in media_dict is not a POSIX: {type(media_dict['File Path'])}"
        )

    logger.info(f"Media dict for adstream: \n{json.dumps(media_dict, indent=4)}")
    return media_dict


def get_endpoint():
    """
    Select an API endpoint from the list of available Vantage servers.
    """
    for endpoint in endpoint_list:
        if endpoint_check(endpoint):
            logger.info(f"{endpoint.upper()} online status is confirmed.")
            return endpoint
        else:
            logger.error(
                f"{endpoint.upper()} is not active or unreachable, please check the Vantage SDK service on the host."
            )
    raise Exception("Unable to reach any available Vantage Endpoints.")


def endpoint_check(endpoint):
    """
    Check the online status of an API endpoint.
    """
    root_uri = f"http://{endpoint}:8676"

    try:
        response = requests.get(f"{root_uri}/REST/Domain/Online").json()
        status = response.get("Online", False)
        logger.info(f"Endpoint - {endpoint} has the status of {status}")
        return status
    except requests.exceptions.RequestException:
        logger.error(f"Exception raised on API check for endpoint: {endpoint}.")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    check_workflows(workflow)
