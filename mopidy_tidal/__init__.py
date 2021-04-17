from __future__ import unicode_literals

import logging
import os
import sys

from mopidy import config, ext


__version__ = '0.2.5'

# TODO: If you need to log, use loggers named after the current Python module
logger = logging.getLogger(__name__)

file_dir = os.path.dirname(__file__)
sys.path.append(file_dir)

class Extension(ext.Extension):

    dist_name = 'Mopidy-Tidal'
    ext_name = 'tidal'
    version = __version__

    def get_default_config(self):
        conf_file = os.path.join(os.path.dirname(__file__), 'ext.conf')
        return config.read(conf_file)

    def get_config_schema(self):
        schema = super(Extension, self).get_config_schema()
        schema['username'] = config.String()
        schema['password'] = config.Secret()
        schema['quality'] = config.String(choices=["LOSSLESS", "HIGH", "LOW"])
        return schema

    def setup(self, registry):
        from .backend import TidalBackend
        registry.add('backend', TidalBackend)
