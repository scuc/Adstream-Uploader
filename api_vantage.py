#!/usr/bin/env python3

import inspect
import json
import re
import requests

from pathlib import PureWindowsPath

import config as cfg


config = cfg.get_config()


workflow = config["vantage"]["workflow_list"]["_Info for AdStream Uploads"]
endpoint_list = config["vantage"]["endpoint_list"]
adstream_folders = config["Adstream"]



def check_workflows(workflow): 
    """
    Vantage REST api calls to check workflows for new media and pull variables from jobs.
    """
    
    media_upload_list = []

    api_endpoint = get_endpoint()

    root_uri = f"http://{api_endpoint}:8676/"

    workflow_endpoint = f"{root_uri}/Rest/workflows/{workflow}/jobs"
    workflow_job_object = requests.get(workflow_endpoint)
    
    print(workflow_job_object)

    workflow_json = workflow_job_object.json()

    print(workflow_json)
    jobs_list = workflow_json["Jobs"]

    adstream_upload_list = []

    for job in jobs_list: 
        print(f"JOB: {job} \n")
        job_id = check_jobs(job)

        if ( job_id is not None
            and job_id != "[]" ): 

            kv_dict = get_job_variabes(job_id)
            media_upload_list.append((kv_dict))
            media_dict = create_media_dict(media_upload_list)
            adstream_upload_list.append(media_dict)
        else:
            print("==================== DUPLICATE JOB ==================== \n ")
            continue

    return adstream_upload_list


def check_jobs(job):
    """
    Check job ID against a list of previously processed
    """

    print("==================== CHECK JOB ==================== \n ")
    # for job in jobs_list:
    job_id = job["Identifier"]
    job_state = job["State"]

    with open("job_id_list.txt", "r+") as f:
        contents = f.readlines()
        # for line in contents:
        #     print(f"====================  LINE: {line} ====================\n")
        match = re.search(job_id, " ".join(contents))

        if match != None: 
            print(f"==================== MATCH: {match} ====================\n ")
            job_id = None
        else:
            print(f"==================== MATCH: None  ====================\n ")
            f.write(f"{job_id}, \n")

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
    vars = response["Labels"][0]["Params"]
    print(f"VARS: {vars}\n")

    kv_dict = {}
    for x in vars:
        name = x["Name"]
        value = x["Value"]
        kv_dict.update({name:value})

    return kv_dict


def create_media_dict(media_upload_list):
    """
    use the media upload list to create list of dicts 
    with K:V pair info needed for upload to adstream
    """

    media_dict = {}

    for d in media_upload_list: 
        path = PureWindowsPath(d["File Path"])
        folder = str(path.parent).rsplit('\\', 1)[-1]
        folderId = adstream_folders[folder]

        print(f"AD STREAM FOLDER ID = {folderId}")

        media_dict.update({"folderId": folderId, "File Name": d["File Name"], "File Path": d["File Path"]})


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
                continue
            else:
                endpoint_status_msg = f"\n\n{endpoint.upper()} online status is confirmed.\n"
                return endpoint

        except Exception as e:
            get_ep_exception_msg2 = f"Unable to reach any available Vantage Endpoints."



def endpoint_check(endpoint):
    '''check the online status of an api endpoint'''

    root_uri = 'http://' + endpoint + ':8676'

    source_frame = inspect.stack()[1]
    frame, filename,line_number,function_name,lines,index = source_frame
    source_func = source_frame[3]

    if source_func in ['intro', 'get_endpoint', 'check_vantage_status', 'check_domain_load',
                       'check_job_queue', 'api_submit', 'job_submit']:
        try:
            domain_check = requests.get(
                root_uri + '/REST/Domain/Online')
            domain_check_rsp = domain_check.json()
            endpoint_status = domain_check_rsp['Online']

        except requests.exceptions.RequestException as excp:
            excp_msg2 = f"\n\n Exception raised on API check for endpoint:  {endpoint}.\n\n"
            endpoint_status = ("error")

    else:
        sourcefunc_msg = f"{source_func} is not in the list of endpoint functions."

    return endpoint_status


if __name__ == '__main__':
    check_workflows()
