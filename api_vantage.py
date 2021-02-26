#!/usr/bin/env python3

import inspect
import json
import logging
import re
import requests

from pathlib import PureWindowsPath, PurePosixPath
from sys import platform

import config as cfg


config = cfg.get_config()
logger = logging.getLogger(__name__)


workflow = config["vantage"]["workflow_list"]["_Info for AdStream Uploads"]
endpoint_list = config["vantage"]["endpoint_list"]
adstream_folders = config["Adstream"]
root_unc = config["paths"]["root_unc"]
root_letter = config["paths"]["root_letter"]


def check_workflows(workflow):
    """
    Vantage REST api calls to check workflows for new media and pull variables from jobs.
    """

    media_upload_list = []

    api_endpoint = get_endpoint()

    root_uri = f"http://{api_endpoint}:8676/"

    workflow_endpoint = f"{root_uri}/Rest/workflows/{workflow}/jobs"
    workflow_job_object = requests.get(workflow_endpoint)

    workflow_json = workflow_job_object.json()

    jobs_list = workflow_json["Jobs"]

    job_list_msg = f"New jobs in the workflow: \n\
                        {workflow_json}"
    logger.info(job_list_msg)

    adstream_upload_list = []

    for job in jobs_list:
        if job["Name"] == "_Info for AdStream Uploads":
            continue

        else:
            job_id = check_jobs(job)
            job_msg = f"Checking Vantage job: {job_id}"
            logger.info(job_msg)

        if (job_id is not None
                and job_id != "[]"):

            kv_dict = get_job_variabes(job_id)

            if kv_dict != {}:
                media_upload_list.append((kv_dict))
                media_dict = create_media_dict(media_upload_list)
                adstream_upload_list.append(media_dict)
            else:
                continue
        else:
            dup_job_msg = f"Job ID: {job_id} is a duplicate, skipping"
            logger.info(dup_job_msg)
            continue

    return adstream_upload_list


def check_jobs(job):
    """
    Check job ID against a list of previously processed
    """

    job_id = job["Identifier"]
    job_state = job["State"]

    if job_state == 5:
        check_job_msg = f"checking job: {job_id}"
        job_state_msg = f"job state: {job_state}"
        logger.info(check_job_msg)
        logger.info(job_state_msg)
    else:
        job_id = None
        return job_id

    with open("job_id_list.txt", "r+") as f:
        contents = f.readlines()
        failed_job_text = f"Upload Failed for job id: {job_id}"
        job_list_contents = " ".join(contents)

        job_id_match = re.search(job_id, job_list_contents)
        upload_failed_match = re.search(failed_job_text, job_list_contents)

        if (job_id_match != None
                and upload_failed_match == None):
            job_match_msg = f"Job ID {job_id} already exists in the job list.txt, setting job_id to None"
            logger.info(job_match_msg)
            job_id = None
        else:
            f.write(f"{job_id}\n")
            job_match_msg = f"Job ID {job_id} - does not exist in the job list.txt, orprevious upload attempta failed, return id for processing."
            logger.info(job_match_msg)

        f.close()
    return job_id


def get_job_variabes(job_id):
    """
    Get the job variables from the vantage workflow. 
    """
    api_endpoint = get_endpoint()
    root_uri = f"http://{api_endpoint}:8676/"

    output_endpoint = f"{root_uri}/Rest/jobs/{job_id}/outputs"
    r = requests.get(output_endpoint)
    response = r.json()
    print(f"================== RESPONSE: {response} ============= ")
    if response["Labels"] != []:

        vars = response["Labels"][0]["Params"]

        kv_dict = {}
        kv_dict.update({"Job Id": job_id})

        for x in vars:
            name = x["Name"]
            value = x["Value"]
            kv_dict.update({name: value})

        job_dict_msg = f"Variables for Job ID {job_id}:  {kv_dict}"
        logger.info(job_dict_msg)

    else:
        kv_dict = {}
        job_dict_msg = f"Variables for Job ID {job_id} are empty, returning empty dict {{}}"
        logger.info(job_dict_msg)

    return kv_dict


def create_media_dict(media_upload_list):
    """
    use the media upload list to create list of dicts 
    with K:V pair info needed for upload to adstream
    """

    media_dict = {}

    for d in media_upload_list:

        job_id = d["Job Id"]
        letter_path = d["File Path"]
        unc_path = letter_path.replace(root_letter, root_unc)
        path = PureWindowsPath(unc_path)
        folder = str(path.parent).rsplit('\\', 1)[-1]

        if folder != "_DeployToAdStream":

            folderId = adstream_folders[folder]
            filename = d["File Name"]
        else:
            continue

        if platform == "darwin":
            tmp_path = d["File Path"].replace("T:\\", "/Volumes/Quantum2/")
            tmp_path2 = tmp_path.replace("\\", "/")
            path = PurePosixPath(tmp_path2)
        else:
            path = PureWindowsPath(path)

        media_dict.update(
            {
                "Job Id": job_id,
                "folderId": folderId,
                "File Name": filename,
                "File Path": path,
            }
        )

    media_upload_dict_msg = f"Media dict for adstream:  \n\
        {media_dict}"
    logger.info(media_upload_dict_msg)

    return media_dict


# ===================== API ENPOINTS CHECKS ======================= #

def get_endpoint():
    """
    Select an api endpoint from the list of available Vantage servers.
    """
    for endpoint in endpoint_list:
        try:
            endpoint_status = endpoint_check(endpoint)

            if endpoint_status != True:
                endpoint_status_msg = f"\n\n{endpoint.upper()} is not active or unreachable, \
                        please check the Vantage SDK service on the host.\n"
                logger.error(endpoint_status_msg)
                continue
            else:
                endpoint_status_msg = f"{endpoint.upper()} online status is confirmed."
                logger.info(endpoint_status_msg)
                return endpoint

        except Exception as e:
            get_ep_exception_msg2 = f"Unable to reach any available Vantage Endpoints."
            logger.error(get_ep_exception_msg2)


def endpoint_check(endpoint):
    """
    check the online status of an api endpoint
    """

    root_uri = 'http://' + endpoint + ':8676'

    try:
        domain_check = requests.get(
            root_uri + '/REST/Domain/Online')
        domain_check_rsp = domain_check.json()
        endpoint_status = domain_check_rsp['Online']

    except requests.exceptions.RequestException as excp:
        excp_msg2 = f"\n\n Exception raised on API check for endpoint:  {endpoint}.\n\n"
        endpoint_status = ("error")
        logger.error(excp_msg2)

    endpoint_status_msg = f"Endpoint - {endpoint} has the status of {endpoint_status}"
    logger.info(endpoint_status_msg)

    return endpoint_status


if __name__ == '__main__':
    check_workflows()
