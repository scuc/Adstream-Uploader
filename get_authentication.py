import base64
import hashlib
import hmac
import requests
import time

import config as cfg

config = cfg.get_config()
key = config['creds']['key']
secret_key = config['creds']['secret']


def get_auth():

    epoch = str(round(time.time()))
    message = bytes(key + epoch, 'utf-8')
    secret = bytes(secret_key, 'utf-8')

    signature = base64.b64encode(
        hmac.new(secret, message, digestmod=hashlib.sha256).digest())
    hash_decode = signature.decode('utf-8')
    token = f"{key}:{hash_decode}:{epoch}"
    auth = f"A5-API {token}"
    return auth