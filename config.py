#! /usr/bin/env python3

import os

import yaml


def get_config():
    """
    Setup configuration and credentials
    """
    # path = "/Users/admin/Scripts/AdStream-Uploader/config.yaml"
    path = "/Users/cucos001/GitHub/Adstream-Uploader/config.yaml"

    with open(path, "rt") as f:
        config = yaml.safe_load(f.read())

    return config


def ensure_dirs(source_path):
    """
    Check source directory for required folders.
    """
    owd = os.getcwd()
    dirs = ["_logs", "json"]
    os.chdir(source_path)

    for dir in dirs:
        if not os.path.exists(dir):
            os.makedirs(dir)
    os.chdir(owd)
    return
