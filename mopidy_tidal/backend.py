from __future__ import unicode_literals

import logging
import os
import sys
import json

from mopidy import backend

from pykka import ThreadingActor

from tidalapi import Config, Session, Quality

from mopidy_tidal import library, playback, playlists


logger = logging.getLogger(__name__)


class TidalBackend(ThreadingActor, backend.Backend):
    def __init__(self, config, audio):
        super(TidalBackend, self).__init__()
        self._session = None
        self._config = config
        self._username = config['tidal']['username']
        self._password = config['tidal']['password']
        self.playback = playback.TidalPlaybackProvider(audio=audio,
                                                       backend=self)
        self.library = library.TidalLibraryProvider(backend=self)
        self.playlists = playlists.TidalPlaylistsProvider(backend=self)
        self.uri_schemes = ['tidal']

    def oauth_login_new_session(self, oauth_file):
        # create a new session
        self._session.login_oauth_simple(function=logger.info)
        if self._session.check_login():
            # store current OAuth session
            data = {}
            data['token_type'] = {'data': self._session.token_type}
            data['session_id'] = {'data': self._session.session_id}
            data['access_token'] = {'data': self._session.access_token}
            data['refresh_token'] = {'data': self._session.refresh_token}
            with open(oauth_file, 'w') as outfile:
                json.dump(data, outfile)

    def on_start(self):
        quality = self._config['tidal']['quality']
        logger.info("Connecting to TIDAL.. Quality = %s" % quality)
        config = Config(quality=Quality(quality))
        self._session = Session(config)
        oauth_file = os.path.join(os.getenv("HOME"), '.config/', 'tidal-oauth.json')
        try:
            # attempt to reload existing session from file
            with open(oauth_file) as f:
                logger.info("Loading OAuth session from %s..." % oauth_file)
                data = json.load(f)
                self._session.load_oauth_session(
                    data['session_id']['data'],
                    data['token_type']['data'],
                    data['access_token']['data'],
                    data['refresh_token']['data']
                )
        except:
            logger.info("Could not load OAuth session from %s" % oauth_file)

        if not self._session.check_login():
            logger.info("Creating new OAuth session...")
            self.oauth_login_new_session(oauth_file)

        if self._session.check_login():
            logger.info("TIDAL Login OK")
        else:
            logger.info("TIDAL Login KO")

