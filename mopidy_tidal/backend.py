from __future__ import unicode_literals

import logging
import threading
import traceback
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from functools import partial, wraps
from string import whitespace

try:
    from urllib import unquote
except ImportError:
    from urllib.parse import unquote

from mopidy import backend

from pykka import ThreadingActor

from tidalapi import Config, Session, Quality

from mopidy_tidal import library, playback, playlists, auth_html


logger = logging.getLogger(__name__)


class TidalBackend(ThreadingActor, backend.Backend):
    def __init__(self, config, audio):
        super(TidalBackend, self).__init__()
        self.session = None
        self._config = config
        self._token = config['tidal']['token']
        self._oauth = config['tidal']['oauth']
        self._oauth_port = config['tidal']['oauth_port']
        self.quality = self._config['tidal']['quality']
        self.playback = playback.TidalPlaybackProvider(audio=audio,
                                                       backend=self)
        self.library = library.TidalLibraryProvider(backend=self)
        self.playlists = playlists.TidalPlaylistsProvider(backend=self)
        self.uri_schemes = ['tidal']

    def on_start(self):
        logger.info("Connecting to TIDAL.. Quality = %s" % self.quality)
        config = Config(self._token, self._oauth, quality=Quality(self.quality))
        self.session = Session(config)
        self.start_oauth_deamon()

    def start_oauth_deamon(self):
        handler = partial(HTTPHandler, self.session)
        daemon = threading.Thread(
            name="TidalOAuthLogin",
            target=HTTPServer(('', self._oauth_port), handler).serve_forever
        )
        daemon.setDaemon(True)  # Set as a daemon so it will be killed once the main thread is dead.
        daemon.start()


def catch(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error('%s: %s', e.__class__.__name__, e)
            logger.error('%s(%s, %s)', func.__name__,
                         ', '.join(str(a) for a in args),
                         ', '.join('{}={}'.format(str(k), str(v)) for k, v in kwargs.items()))
            raise
    return wrapper


class HTTPHandler(BaseHTTPRequestHandler, object):

    def __init__(self, session, *args, **kwargs):
        self.session = session
        self.code_verifier = None
        super(HTTPHandler, self).__init__(*args, **kwargs)

    @catch
    def do_GET(self):
        self.code_verifier, authorization_url = self.session.login_part1()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(auth_html.body(authurl=authorization_url))

    @catch
    def do_POST(self):
        content_length = int(self.headers.getheader('content-length', 0))
        body = self.rfile.read(content_length)
        try:
            form = {k: v for k, v in (p.split("=", 1) for p in body.split("&"))}
            code_url = unquote(form['code'].strip(whitespace))
        except:
            self.send_response(400)
            self.end_headers()
            self.wfile.write("Malformed request")
            raise
        else:
            try:
                self.session.login_part2(self.code_verifier, code_url)
                self.send_response(200)
                self.end_headers()
                self.wfile.write("Success! Autorefresh is on. Enjoy your music!")
            except:
                self.send_response(401)
                self.end_headers()
                self.wfile.write("Failed to get final key! :(")
                raise
