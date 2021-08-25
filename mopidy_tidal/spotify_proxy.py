import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

class SpotifyProxy:
    def __init__(self, client_id, client_secret):
        self.set_credentials(client_id, client_secret)
        
    def set_credentials(self, client_id, client_secret):
        self.credentials = SpotifyClientCredentials(
            client_id=client_id, 
            client_secret=client_secret
        )

    def get_song_info(self, lz_uri):
        spotify = spotipy.Spotify(client_credentials_manager = self.credentials)
        results = spotify.tracks([lz_uri])
        if len(results['tracks']) > 0:
            track = results['tracks'][-1]
            title = track["name"]
            artists = [a["name"] for a in track["artists"]]
            return {"title": title, "artists": artists}
        else:
            return None
