import os
import markdown
from . import config

def get_api_key():
    key_path = os.path.join(config.BASE_DIR, 'key.txt')
    if os.path.exists(key_path):
        with open(key_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return ""

def md_to_html(text):
    return markdown.markdown(text, extensions=['extra', 'nl2br', 'sane_lists'])