import os
import json

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'api_keys.json')

def save_api_key(service, key):
    keys = load_api_keys()
    keys[service] = key
    with open(CONFIG_PATH, 'w') as f:
        json.dump(keys, f)

def load_api_keys():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    return {}

def get_api_key(service):
    keys = load_api_keys()
    return keys.get(service, '')
