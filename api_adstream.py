import base64
import hashlib
import hmac
import json
import os
import pprint
import requests
import time

from pathlib import Path

import config as cfg
import get_authentication as getauth


config = cfg.get_config()
json_path = config['paths']['json_path']
media_path = config['paths']['media_path']


def new_media_creation(adstream_upload_list):
    """
    Three step process to add media into the Adstream platorm. 
    1 - POST request  to register a placeholder for the new media.
    2 - PUT request  - Use the response parameters from the register to upload the media
    3 - POST request - complete the media creation with a put request. 

    """

    for media in adstream_upload_list: 
        registered_media = register_media(media["File Name"])

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

        print(f"============ UPLOAD PARAMS =========== \n\
            upload_params={{\n\
                    media_path: {media_path},\n\
                    fileId: {fileId},\n\
                    url: {url},\n\
                    reference: {reference},\n\
                    storageId: {storageId},\n\
                    status: {status},\n\
                    filename: {filename},\n\
                    folderId: {folderId},\n\
                }}"
        )

        media_params = upload_media(**upload_params)
        media_complete(**media_params)
        print("============ NEW MEDIA CREATION COMPLETE =========== \n")


def register_media(filename):
    """
    POST request to register a placeholder for new media. 
    """

    print("========== BEGIN REGISTER MEDIA ============\n")

    auth = getauth.get_auth()
    folderId = "5ff36b0746e0fb00010ef4b5"
    url_register_media = f"https://a5.adstream.com/api/v2/folders/{folderId}/media"
    
    json = {"filename" : filename}
    headers = {"Authorization": auth}
    r = requests.post(url_register_media, headers=headers, json=json)
    response = r.json()
    print(response)
    return response


def upload_media(**upload_params):
    """
    PUT request to upload the media file to the AdStream platform. 
    """

    print("========== BEGIN MEDIA UPLOAD ============\n")

    auth = getauth.get_auth()

    test_mov = Path(media_path, 'test-02.mov')
    url = upload_params["url"]
    filename = upload_params["filename"]
    fileId = upload_params["fileId"]
    storageId = upload_params["storageId"]
    folderId = upload_params["folderId"]
    headers = {"Authorization": auth}

    with open(test_mov, 'rb') as f:
        r = requests.put(url, files={filename: f})
        response = r.text
        status_code = r.status_code
        encoding = r.encoding

        print(f"encoding: {encoding}")
        print(f"status_code:  {status_code}")
        print(f"post response:  {response}")

    media_params = {"filename" : filename, "folderId": folderId, "storageId": storageId, "fileId": fileId}
    
    print("==========  MEDIA UPLOAD COMPLETE ============ \n ")
    return media_params


def media_complete(**media_params ):
    """
    POST request to complete the addition of new media file to Adstream platform. 
    """

    print("========== BEGIN ""MEDIA COMPLETE"" ============\n")

    auth = getauth.get_auth()

    print(media_params)
    folderId = media_params["folderId"]
    fileId = media_params["fileId"]
    filename = media_params["filename"]
    storageId = media_params["storageId"]

    url_media_complete = f"https://a5.adstream.com/api/v2/folders/{folderId}/media/{fileId}"
    
    json = {
        "meta": {
            "common": {
                "name": f"{filename}"
            }
        },
        "subtype": "element",
    }

    headers = {"Authorization": auth}
    params = {'fileId': fileId, "folderId": folderId}
    r = requests.post(url_media_complete, headers=headers, json=json, params = params)
    status_code = r.status_code
    response = r.json()
    encoding = r.encoding

    print(f"encoding: {encoding}")
    print(f"status_code:  {status_code}")
    print(f"post response:  {response}")

    return


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

        # except requests.exceptions.RequestException as e:
        #     raise SystemExit(e)

        # print(f"SIGNATURE: {signature}")
        # print(f"HASH-DECODE: {hash_decode}")
        # print(f'TOKEN: {token}')
        # print(f"HEADERS: {headers}")
        # print("")
        # print(f"URL:  {r.url}")
        # print("")
        # print(r.request.headers)
        # print("")
        # print(r.request.body)
        # print("")
        # print(r.headers)
        # print("")
        # pprint.pprint(r.json())

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
