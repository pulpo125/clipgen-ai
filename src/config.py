from os.path import dirname, abspath, join

import yaml
from easydict import EasyDict

# ==================================================
PROJECT_ROOT = dirname(abspath(dirname(__file__)))
# ==================================================


def load_yaml(path: str, easy_dict=True) -> dict:
    with open(join(PROJECT_ROOT, path)) as f:
        cfg = yaml.safe_load(f)
    if easy_dict:
        return EasyDict(cfg)
    else:
        return cfg


cfg = load_yaml("conf/service.yaml")
cfg_engine = load_yaml("conf/engine.yaml")
