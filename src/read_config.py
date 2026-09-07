import json
import os

from dotenv import load_dotenv

load_dotenv()

def read_json(file_path:str):
    return json.loads(open(file_path).read())

def get_config_dict():
    return read_json("config.json")

def get_config(*keys:str) -> list|str|bool:
    configs = []
    config_dict = get_config_dict()
    if len(keys)==1:
        return config_dict[keys[0]]
    for key in keys:
        configs.append(config_dict[key])
    if len(configs) == 1:
        return configs[0]
    return configs

def get_credentials() -> dict:
    username = os.getenv("OTEC_USERNAME")
    password = os.getenv("OTEC_PASSWORD")
    if not username or not password:
        return {}
    return {"OTEC_USERNAME": username, "OTEC_PASSWORD": password}