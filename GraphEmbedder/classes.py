from bs4 import BeautifulSoup
import deezer
import base64
import requests
import json
from urllib.parse import urlencode

class SpotifyAPIUser():
    def __init__(self, client_id, secret_id):
        self.client_id = client_id
        self.secret_id = secret_id
        self._create_token()
        self._create_auth_header()

    def _create_token(self):
        auth_string = self.client_id + ':' + self.secret_id
        auth_bytes = auth_string.encode("utf-8")
        auth_base64 = str(base64.b64encode(auth_bytes), "utf-8")
        url = "https://accounts.spotify.com/api/token"
        
        headers = {
            "Authorization": "Basic " + auth_base64,
            "Content-Type": "application/x-www-form-urlencoded"
        }

        data = {"grant_type": "client_credentials"}
        result = requests.post(url, headers=headers, data=data)
        json_result = json.loads(result.content)
        self.token = json_result["access_token"]

    def _create_auth_header(self):
        self.header = {"Authorization": "Bearer " + self.token}

    def get_tracks_from_playlist(self, playlist_id):
        list_of_tracks = []
        for i in range(10):
            url = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks?offset={100*i}'
            response = requests.get(url, headers=self.header).content.decode('utf-8')
            
            if len(json.loads(response)['items']) > 0:
                for item in json.loads(response)['items']:
                    artist_name = item['track']['artists'][0]['name']
                    track_name = item['track']['name']
                    list_of_tracks.append((track_name, artist_name))
                
        return list_of_tracks

