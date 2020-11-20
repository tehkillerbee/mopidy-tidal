import logging
import threading
import traceback
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from functools import partial, wraps
from string import whitespace

from backend import unquote

logger = logging.getLogger(__name__)

HTML_BODY = """<!DOCTYPE html>
<html>
<head>
<title>TIDAL OAuth Login</title>
</head>
<body>

<h1>KEEP THIS TAB OPEN</h1>
<a href={authurl} target="_blank" rel="noopener noreferrer">Click here to be forwarded to TIDAL Login page</a>
<p>...then, after login, copy URL of the page you ended up to.</p>
<p>Probably a "not found" page, nevertheless we need the URL</p>
<form method="post">
  <label for="code">Paste here your final URL location:</label>
  <input type="hidden" id="usrkey" name="usrkey" value="{usrkey}">
  <input type="url" id="code" name="code">
  <input type="submit" value="Submit">
</form>

</body>
</html>
""".format


def start_oauth_deamon(session, port):
    handler = partial(HTTPHandler, session)
    daemon = threading.Thread(
        name="TidalOAuthLogin",
        target=HTTPServer(('', port), handler).serve_forever
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
        super(HTTPHandler, self).__init__(*args, **kwargs)

    @catch
    def do_GET(self):
        code_verifier, authorization_url = self.session.login_part1()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(HTML_BODY(authurl=authorization_url, usrkey=code_verifier))

    @catch
    def do_POST(self):
        content_length = int(self.headers.getheader('content-length', 0))
        body = self.rfile.read(content_length)
        try:
            form = {k: v for k, v in (p.split("=", 1) for p in body.split("&"))}
            code_url = unquote(form['code'].strip(whitespace))
            usr_key = unquote(form['usrkey'])
        except:
            self.send_response(400)
            self.end_headers()
            self.wfile.write("Malformed request")
            raise
        else:
            try:
                self.session.login_part2(usr_key, code_url)
                self.send_response(200)
                self.end_headers()
                self.wfile.write("Success! Autorefresh is on. Enjoy your music!")
            except:
                self.send_response(401)
                self.end_headers()
                self.wfile.write("Failed to get final key! :(")
                raise
