#!/usr/bin/env python3
import datetime
import json
import logging
import os
import requests
import time

from pathlib import Path

import config as cfg
import get_authentication as getauth


config = cfg.get_config()
# json_path = config['paths']['json_path']
# media_path = config['paths']['media_path']
root_folderId = config['Adstream']['NatGeoPromoExchange']

logger = logging.getLogger(__name__)


def new_media_creation(adstream_upload_list):
    """
    Three step process to add media into the Adstream platorm. 
    1 - POST request  to register a placeholder for the new media.
    2 - PUT request  - Use the response parameters from the register to upload the media
    3 - POST request - complete the media creation with a put request. 

    """

    adstream_start_msg = f"\n \n ============== Starting media upload to Adstream =================\n"
    logger.info(adstream_start_msg)

    adstream_list_msg = f"\n  ============ AdStream NEW MEDIA LIST ===========:\n {adstream_upload_list} \n"
    logger.info(adstream_list_msg)

    media_summary = {"Uploaded Files": [], "Failed Uploads": []}

    for media in adstream_upload_list:
        # Short pause between uploads so Adstream does not think script is a DOS attack.
        time.sleep(10)

        if media == {}:
            continue
        else:
            vantage_job_id = media["Job Id"]
            registered_media = register_media(
                media["File Name"], vantage_job_id)

        if registered_media != None:
            fileId = registered_media[0]["id"]
            url = registered_media[0]["url"]
            reference = registered_media[0]["reference"]
            storageId = registered_media[0]["storageId"]
            status = registered_media[0]["status"]
            filename = registered_media[0]["filename"]

            filepath = media["File Path"]
            folderId = media["folderId"]

            upload_params = {
                "media_path": filepath,
                "fileId": fileId,
                "url": url,
                "reference": reference,
                "storageId": storageId,
                "status": status,
                "filename": filename,
                "folderId": folderId,
            }

            upload_params_msg = f"\n \n ============ AdStream UPLOAD PARAMS =========== \n\
                upload_params={{\n\
                            media_path: {filepath},\n\
                            fileId: {fileId},\n\
                            url: {url},\n\
                            reference: {reference},\n\
                            storageId: {storageId},\n\
                            status: {status},\n\
                            filename: {filename},\n\
                            folderId: {folderId},\n\
                        }}"
            logger.info(upload_params_msg)
        else:
            media_register_err_msg = f"Media Registration ERROR for {vantage_job_id}, moving to next."
            logger.error(media_register_err_msg)
            continue

        media_params = upload_media(vantage_job_id, **upload_params)

        if media_params != None:
            media_finish = media_complete(
                vantage_job_id, filepath, **media_params)
        else:
            media_upload_err_msg = f"Media Upload ERROR for {vantage_job_id}, moving to next upload."
            logger.error(media_upload_err_msg)
            continue

        if media_finish == True:
            media_summary["Uploaded Files"].append(filename)
            media_complete_msg = f"{filename} now available in the adstream web interface."
            logger.info(media_complete_msg)
        else:
            media_summary["Failed Uploads"].append(filename)
            media_complete_err_msg = f"Media completetion ERROR for {vantage_job_id}, moving to next."
            logger.error(media_complete_err_msg)
            continue

    return media_summary


def register_media(filename, vantage_job_id):
    """
    POST request to register a placeholder for new media. 
    """

    try:
        register_media_msg = f"Registering new media placeholder for:  {filename}"
        logger.info(register_media_msg)

        auth = getauth.get_auth()
        folderId = root_folderId
        url_register_media = f"https://a5.adstream.com/api/v2/folders/{folderId}/media"

        json = {"filename": filename}
        headers = {
            "Authorization": auth,
            "Content-Type": "application/json",
            "Accept-Encoding": None
        }
        r = requests.post(url_register_media, headers=headers, json=json)
        response = r.json()

        headers = r.headers
        r.connection.close()

        headers_register_media_msg = f"MEDIA REGISTER HEADERS:\n {headers}"
        logger.info(headers_register_media_msg)

        register_resp_msg = f"MEDIA REGISTER RESPONSE: \n {response}"
        logger.info(register_resp_msg)

        status = response[0]['status']
        rsp_status_msg = f"Response for media Registration: {status}"
        logger.info(rsp_status_msg)

        if response[0]['status'] == "succeeded":

            rsp_sucess_msg = f"Resgister media sucessful for: {filename}"
            logger.info(rsp_sucess_msg)

        else:
            rsp_fail_msg = f"Media registration error for {filename}, status = {status}"
            logger.error(rsp_fail_msg)

        return response

    except Exception as e:
        reg_err_msg = f"Exception on Register Media step for {filename} \n {e}"
        logger.error(reg_err_msg)
        cleanup_media_fail(vantage_job_id, filename)
        return None


def upload_media(vantage_job_id, **upload_params):
    """
    PUT request to upload the media file to the AdStream platform. 
    """

    auth = getauth.get_auth()

    media_path = upload_params["media_path"]
    filename = upload_params["filename"]

    media = Path(media_path)
    url = upload_params["url"]
    fileId = upload_params["fileId"]
    storageId = upload_params["storageId"]
    folderId = upload_params["folderId"]
    reference = upload_params["reference"]
    # headers = {
    #             "Authorization": auth,
    #             "Content-Type": "application/json",
    #             "Content-Length": "580",
    #             "Accept-Encoding": None
    # }

    media_upload_msg = f"Begin media upload for: {filename}"
    logger.info(media_upload_msg)

    try:
        with open(media, 'rb') as f:
            data = f.read()
            r = requests.put(url, data=data)
            status_code = r.status_code
            encoding = r.encoding
            headers = r.headers

        r.connection.close()

        upload_headers_msg = f"MEDIA UPLOAD HEADERS:\n {headers}"
        logger.info(upload_headers_msg)

        upload_params = {"filename": filename, "folderId": folderId,
                         "storageId": storageId, "fileId": fileId}

        upload_complete_msg = f"Uplaod to adstream complete for: {filename}"
        upload_params_msg = f"Media params for {filename}: \n {upload_params}"
        logger.info(upload_complete_msg)
        logger.info(upload_params_msg)

        return upload_params

    except Exception as e:
        upload_err_msg = f"Exception on the Media Upload step for {filename}: \n {e}"
        logger.error(upload_err_msg)
        cleanup_media_fail(vantage_job_id, filename)
        return None


def media_complete(vantage_job_id, filepath, **media_params):
    """
    POST request to complete the addition of new media file to Adstream platform. 
    """

    auth = getauth.get_auth()

    folderId = media_params["folderId"]
    fileId = media_params["fileId"]
    filename = media_params["filename"]
    storageId = media_params["storageId"]

    start_media_compelete_msg = f"Starting the ""media compeletion"" step for {fileanme}"
    logger.info(start_media_compelete_msg)

    try:
        url_media_complete = f"https://a5.adstream.com/api/v2/folders/{folderId}/media/{fileId}"

        json = {
            "meta": {
                "common": {
                    "name": f"{filename}"
                }
            },
            "subtype": "element",
        }

        headers = {
            "Authorization": auth,
            "Content-Type": "application/json",
            "Accept-Encoding": None
        }

        params = {'fileId': fileId, "folderId": folderId}
        r = requests.post(url_media_complete, headers=headers,
                          json=json, params=params)
        status_code = r.status_code
        response = r.json()
        encoding = r.encoding

        headers = r.headers

        headers_media_complete_msg = f"MEDIA COMPLETE HEADERS:\n {headers}"
        logger.info(headers_media_complete_msg)

        r.connection.close()

        response_msg = f"\n\
                        {{\n\
                        Status Code: {status_code} \n\
                        Response: {response}\n\
                        Encoding = {encoding}\n\
                        }}"
        logger.info(response_msg)

        end_media_complete_msg = f"Post response for media complete request: \n {response}"
        logger.info(end_media_complete_msg)

        if str(status_code) == "201":
            # os.remove(filepath)
            # remove_msg = f"{filename} deleted from location: {filepath}"
            # logger.info(remove_msg)
            media_finish = True
        else:
            bad_statuscode_msg = f"Unexpected status code returned: {status_code}\n\
                                   Source file was not removed from the filesystem."
            logger.info(bad_statuscode_msg)
            media_finish = False

        return media_finish

    except Exception as e:
        upload_err_msg = f"Exception on the Media Complete step for {filename}: \n {e}"
        logger.error(upload_err_msg)
        cleanup_media_fail(vantage_job_id)
        return None


def cleanup_media_fail(vantage_job_id, filename):
    """
    CleanUp of the JobID List if the Adstream media creation fails. 
    """
    media_cleanup_msg = f"Starting Job ID clean up for - {vantage_job_id}"
    logger.info(media_cleanup_msg)
    with open("job_id_list.txt", "rt+") as f:
        contents = f.readlines()
        f.close
    with open("job_id_list.txt", "wt+") as f:
        for line in contents:
            if line.strip("\n") != vantage_job_id:
                f.write(line)
            else:
                timenow = datetime.datetime.today()
                timestamp = timenow.strftime("%Y-%m-%d, %H:%M:%S"),
                new_line = line.replace(
                    vantage_job_id, f"[ {timestamp} - Upload Failed for job id: {vantage_job_id} ]")
                f.write(new_line)
                cleanup_msg = f"Adstream Media Creation Failure - Job ID: {vantage_job_id}, Filename: {filename}"
                logger.info(cleanup_msg)
        f.close


# ===================== API Actions - UNUSED ======================= #


def get_folder(folderId):

    auth = getauth.get_auth()
    url = f"https://a5.adstream.com/api/v2/folders/" + folderId

    headers = {"Authorization": auth}
    params = {"folderId": folderId}

    r = requests.get(url, headers=headers)
    response = r.json()
    print(response)


def get_folders():

    url = "https://a5.adstream.com/api/v2/folders"

    os.chdir(json_path)
    epoch = str(round(time.time()))
    filename = "adstream_folders_" + epoch + ".json"
    page_num = 1

    while True:
        auth = getauth.get_auth()

        headers = {"Authorization": auth}
        params = {"page": page_num}

        print("LOOP")

        r = requests.get(url, headers=headers, params=params)
        response = r.json()
        print(response)

        with open(filename, "a+") as folders_file:
            if response == []:
                print("BREAK")
                break
            elif page_num == 1:
                json.dump(response, folders_file, indent=4, sort_keys=True)
                print("OPTION 1:  " + str(page_num))
                time.sleep(5)
                page_num += 1
            else:
                json.dump(response, folders_file,
                          indent=4, sort_keys=True)
                print("OPTION 2:  " + str(page_num))
                time.sleep(5)
                page_num += 1

        folders_file.close()

    print("GET FOLDERS DONE")
    return


def search_files():
    auth = getauth.get_auth()
    query = "test-02.mov"
    url = "https://a5.adstream.com/api/v2/files"

    headers = {"Authorization": auth}
    params = {"query": query}

    r = requests.get(url, headers=headers, params=params)
    response = r.json()
    print(response)


def get_project(projectId="5ff36b0746e0fb00010ef4b6"):
    auth = getauth.get_auth()

    url = f"https://a5.adstream.com/api/v2/projects/{projectId}"
    headers = {"Authorization": auth}
    params = {"projectId": projectId}

    r = requests.get(url, headers=headers, params=params)
    response = r.json()
    print(response)


def get_projects():
    auth = getauth.get_auth()
    os.chdir(json_path)

    url = 'https://a5.adstream.com/api/v2/projects'
    auth = auth
    headers = {"Authorization": auth}
    epoch = str(round(time.time()))
    page_num = 1
    filename = "adstream_projects_" + epoch + ".json"

    while True:
        print("LOOP")
        params = {"page": page_num}
        r = requests.get(url, headers=headers, params=params)
        response = r.json()
        print(type(response))
        print(response)

        with open(filename, "a+") as projects_file:
            if response == []:
                print("BREAK")
                break
            elif page_num == 1:
                json.dump(response, projects_file, indent=4, sort_keys=True)
                print("OPTION 1:  " + str(page_num))
                page_num += 1
            else:
                json.dump(response, projects_file,
                          indent=4, sort_keys=True)
                print("OPTION 2:  " + str(page_num))
                page_num += 1

        projects_file.close()

    print("GET PROJECTS DONE")
    return


def compare_projects(json_file):
    '''
    Get an updated list of projects and compare the new list to
    the previously pulled list of the projects. Check for any 
    differences between the two lists. Return the names of 
    any new projects. 
    '''
    print("COMPARE PROJECTS")
    auth = getauth.get_auth()
    new_projects = get_projects(auth)
    old_projects = json_file

    with open(new_projects, "r") as new_json_file, open(old_projects) as old_json_file:
        data_old = json.load(old_projects)
        data_new = json.load(new_projects)

    print(f"DATA OLD: {len(data_old)}")
    print(f"DATA NEW: {len(data_new)}")

    for proj in data_old:
        print(proj['meta']['common']['name'])

    if not len(data_new) == len(data_old):
        print("NOT EQUAL")
    else:
        print("EQUAL")

    # old_projects.unlink()
    print("COMPARE DONE")


def create_project():
    """
    Create a new project in the root directory
    """

    auth = getauth.get_auth()

    url = "https://a5.adstream.com/api/v2/projects"
    project_name = "STEVE-TEST-3"
    json = {"meta": {
        "common": {
            "name": f"{project_name}",
            "published": False,
            "projectMediaType": ["Broadcast"]
        }
    }
    }

    headers = {"Authorization": auth}
    try:
        r = requests.post(url, headers=headers, json=json)
        response = r.json()
        print(response)

    except requests.exceptions.RequestException as e:
        raise SystemExit(e)

    return


def create_project_folder():
    """
    Create a new folder in a specific project 
    """

    auth = getauth.get_auth()

    url = "https://a5.adstream.com/api/v2/folders"
    project_id = "601c52c5c9e77c000171e893"
    folder_name = "Steves-TEST-Upload-Folder-No2"
    json = {
        "parent": f"{project_id}",
        "meta": {
            "common": {
                "name": f"{folder_name}"
            }
        }
    }

    headers = {"Authorization": auth}
    try:
        r = requests.post(url, headers=headers, json=json)
        response = r.json()
        print(response)

    except requests.exceptions.RequestException as e:
        raise SystemExit(e)

    return


if __name__ == '__main__':
    create_project()
