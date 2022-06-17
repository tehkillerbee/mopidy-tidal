_ctx = {
    'config': None,
}


def set_config(cfg):
    _ctx['config'] = cfg


def get_config():
    assert _ctx.get('config'), 'Extension configuration not set'
    return _ctx['config']
