import pandas as pd
import numpy as np
import requests
import json
import math

pd.set_option('display.max_colwidth', 100)


class SpotifyUser:

    def __init__(self, auth_token, client_id, user_id):
        self.auth_token = auth_token
        self.client_id = client_id
        self.user_id = user_id

    def last_played_tracks(self, limit=10):
        url = f'https://api.spotify.com/v1/me/player/recently-played?limit={limit}'
        response_json = self._get_api_request(url)
        # return response_json
        return pd.DataFrame([(i["track"]['artists'][0]['name'], i['track']['name']) for i in response_json['items']],
                            columns=['artist', 'song'])

    def get_top(self, _type, time, limit, offset):
        url = f'https://api.spotify.com/v1/me/top/{_type}?time_range={time}&limit={limit}&offset={offset}'
        response_json = self._get_api_request(url)
        if _type == 'artists':
            return pd.DataFrame([(i['name'], i['popularity'], i['followers']['total']) for i in response_json['items']],
                                columns=['name', 'popularity', 'followers'])
        elif _type == 'tracks':
            return pd.DataFrame([(i['name'], i['duration_ms']) for i in response_json['items']],
                                columns=['name', 'duration'])
        else:
            raise ValueError('Must specify artists or tracks')

    def get_playlists(self, limit=50):
        url = f'https://api.spotify.com/v1/me/playlists?limit={limit}'
        response_json = self._get_api_request(url)
        return pd.DataFrame([(i['name'], i['tracks']['href'], i['tracks']['total']) for i in response_json['items']],
                            columns=['name', 'tracks_link', 'total_tracks'])

    def get_playlist_tracks(self, playlist_name, limit=100, offset=0, get_all=False):

        playlists = self.get_playlists()
        link = playlists[playlists['name'] == playlist_name]['tracks_link'].to_string(index=False).strip()

        if not get_all:
            url = f'{link}?limit={limit}&offset={offset}'
            response = self._get_api_request(url)
            return self.get_user_tracks(response)
        else:
            combined_df = []
            n_tracks = playlists[playlists['name'] == playlist_name]['total_tracks'].to_string(index=False).strip()
            upper_limit = int(math.ceil(int(n_tracks) / 100)) * 100
            for i in range(0, upper_limit + 100, 100):
                try:
                    url = f'{link}?limit={limit}&offset={i}'
                    response = self._get_api_request(url)
                    combined_df.append(self.get_user_tracks(response))
                except IndexError:
                    pass
            return pd.concat([*combined_df])

    def add_tracks_to_playlist(self, playlist, track_uris):
        data = json.dumps(track_uris)
        url = f'https://api.spotify.com/v1/playlists/{playlist}/tracks'
        response = self._post_api_request(url, data)
        return response.json()

    def create_playlist(self, name):
        data = json.dumps({
            "name": name,
            "description": "Sent by Python",
            "public": True})
        url = f'https://api.spotify.com/v1/users/{self.user_id}/playlists'
        response = self._post_api_request(url, data)
        response_json = response.json()

        playlist_id = response_json['id']
        return {name: playlist_id}

    def get_artist_id(self, query, _type):

        query_formatted = query.replace(' ', '%20')
        url = f'https://api.spotify.com/v1/search?q={query_formatted}&type={_type}'
        response_json = self._get_api_request(url)
        artist_ids = {}

        for i in response_json['artists']['items']:
            if i['name'].lower() == query:
                artist_ids[i['id']] = i['popularity']

        print("Note there are more than one IDs, the most popular is being returned")
        return max(artist_ids, key=artist_ids.get)

    def get_artists_top_tracks(self, artist_id, country_iso='US'):
        url = f'https://api.spotify.com/v1/artists/{artist_id}/top-tracks?market={country_iso}'
        print(url)
        response_json = self._get_api_request(url)

        tracks_ids = {}

        for i in response_json['tracks']:
            tracks_ids[i['name']] = i['uri']

        return tracks_ids

    def _get_api_request(self, url):
        response = requests.get(
            url,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.auth_token}', })
        
        
        SpotifyUser._check_status_code(response)
        return response.json()

    def _post_api_request(self, url, data):
        response = requests.post(
            url,
            data,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.auth_token}',
            })
        SpotifyUser._check_status_code(response)
        return response
    
    @staticmethod
    def _check_status_code(response):
        if response.status_code in range(200, 299):
            print("Token is valid and we are good to go")
        else:
            raise RuntimeError("Error: invalid status code, ensure the token is correct')
         
    def get_user_tracks(self, response_json):
        artists = []
        tracks = []
        release_date = []
        duration = []
        date_added = []

        for j in range(len(response_json['items'])):
            artists.append(", ".join([(i['name']) for i in response_json['items'][j]['track']['artists']]))
            tracks.append([i['track']['name'] for i in response_json['items']])
            release_date.append(response_json['items'][j]['track']['album']['release_date'])
            duration.append([j['track']['duration_ms'] for j in response_json['items']])
            date_added.append([j['added_at'] for j in response_json['items']])

        return pd.DataFrame(
            [(i, j, k, x, y) for i, j, k, x, y in zip(artists, tracks[0], release_date, duration[0], date_added[0])],
            columns=['artists', 'tracks', 'release_date', 'duration', 'date_added'])
