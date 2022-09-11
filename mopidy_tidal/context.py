_ctx = {
    "config": None,
}


def set_config(cfg):
    _ctx["config"] = cfg


def get_config():
    if not _ctx["config"]:
        raise ValueError("Extension configuration not set.")
    return _ctx["config"]
