import os
from cryptography.fernet import Fernet
from . import config

def load_key():
    if os.path.exists(config.VIDEO_KEY_FILE):
        return open(config.VIDEO_KEY_FILE,'rb').read()
    key = Fernet.generate_key()
    with open(config.VIDEO_KEY_FILE,'wb') as f: f.write(key)
    return key

fernet = Fernet(load_key())