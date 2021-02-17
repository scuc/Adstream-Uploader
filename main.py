
import glob
import json
import os


from pathlib import Path

import api_adstream as api_a
import api_vantage as api_v
import get_authentication as getauth

import config as cfg


config = cfg.get_config()

# adstream_folders = config['Adstream']
# json_path = config['paths']['json_path']
# media_path = config['paths']['media_path']
source_path = config['paths']['source_path']


cfg.ensure_dirs(source_path)


def main(): 

    workflow = config["vantage"]["workflow_list"]["_Info for AdStream Uploads"]

    adstream_upload_list = api_v.check_workflows(workflow)
    print(f"AdStream UPLOAD: {adstream_upload_list}")

    if len(adstream_upload_list) != 0: 

        api_a.new_media_creation(adstream_upload_list)

    else: 
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
    main()
