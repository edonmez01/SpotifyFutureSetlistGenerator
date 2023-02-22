from collections import defaultdict as dd
import os
import requests
import time

from repertorio import Repertorio

import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Define the environment variables SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI, and REPERTORIO_TOKEN.
# More information about these can be found at:
# https://spotipy.readthedocs.io/en/2.22.1/#authorization-code-flow
# https://repertorio.readthedocs.io/en/latest/

# Enter the playlist ID of the playlist you want to generate:
PLAYLIST_ID = '66Mx7JJfRbwBMLKv8I3K9l'

# Enter the names of the bands you want to search, and the search start dates:
BANDS = ['fleshgod apocalypse', 'obscura', 'wolfheart', 'thulcandra', 'hinayana']
SEARCH_START_DATES = ['18-02-2023', '18-02-2023', '18-02-2023', '18-02-2023', '09-09-2021']

# This dictionary can be used to map a song name to a custom string (example usage given below):
CUSTOM_MAP = {
    # 'rotting christ - chaos geneto (the sign of prime creation)': 'rotting christ - the signe of prime creation'
}

REPERTORIO_TOKEN = os.getenv('REPERTORIO_TOKEN')
api = Repertorio(REPERTORIO_TOKEN)
spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(scope='playlist-modify-public'))

playlist_tracks_obj = spotify.playlist_items(PLAYLIST_ID, additional_types=('track',))
playlist_tracks = []
for item in playlist_tracks_obj['items']:
    playlist_tracks.append(item['track']['id'])
spotify.playlist_remove_all_occurrences_of_items(PLAYLIST_ID, playlist_tracks)

for i in range(len(BANDS)):
    max_band_name = 0
    max_song_name = 0
    d = dd(lambda: [])
    band_name = BANDS[i]
    max_band_name = max(max_band_name, len(band_name))
    search_start_date = SEARCH_START_DATES[i]
    limit_day, limit_month, limit_year = (int(n) for n in search_start_date.split('-'))

    artists = None
    success = False
    while not success:
        try:
            artists = api.artists(artistName=band_name, sort='relevance')
            success = True
        except requests.exceptions.HTTPError:
            pass

    artist = artists['artist'][0]
    artist_mbid = artist['mbid']
    page_num = 1
    done = False

    while True:
        setlists = None
        success = False
        while not success:
            try:
                setlists = api.setlists(artistMbid=artist_mbid, p=page_num)
                success = True
            except requests.exceptions.HTTPError as e:
                if str(e)[:3] == '404':
                    success = True

        if not setlists:
            break

        for setlist in setlists['setlist']:
            current_date = setlist['eventDate']
            current_day, current_month, current_year = (int(n) for n in current_date.split('-'))
            if current_year < limit_year\
                    or (current_year == limit_year and current_month < limit_month)\
                    or (current_year == limit_year and current_month == limit_month and current_day < limit_day):
                done = True
                break

            if not setlist['sets']['set']:
                continue

            songlist = []
            for chunk in setlist['sets']['set']:
                songlist += chunk['song']

            for j in range(1, len(songlist) + 1):
                song_name = songlist[j - 1]['name'].lower()
                max_song_name = max(max_song_name, len(song_name))
                if song_name:
                    artist_song_name = band_name + ' - ' + song_name
                    if artist_song_name in CUSTOM_MAP:
                        if not CUSTOM_MAP[artist_song_name]:
                            continue
                        artist_song_name = CUSTOM_MAP[artist_song_name]
                    d[artist_song_name].append((j - .5) / len(songlist))

        page_num += 1
        time.sleep(.2)

        if done:
            break

    out_d = {}
    for k, v in d.items():
        if k:
            out_d[k] = sum(v) / len(v)

    out_d = {k: v for k, v in sorted(out_d.items(), key=lambda x: x[1])}

    for k, v in out_d.items():
        band, song = k.split(' - ', 1)
        spotify_search_query = f'{song} artist:{band}'
        search_result = spotify.search(spotify_search_query, limit=5)
        print(f'{band:>{max_band_name}} - {song:>{max_song_name}}: {v:<20} ({len(d[k]):>2})')
        song_id = search_result['tracks']['items'][0]['id']
        spotify.playlist_add_items(PLAYLIST_ID, (song_id,))
