import sys
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
BANDS = ['cradle of filth', 'devildriver', 'black satellite', 'oni', 'eluveitie', 'omnium gatherum', 'seven spires']
SEARCH_START_DATES = ['08-03-2023', '08-03-2023', '08-03-2023', '08-03-2023', '02-03-2023', '02-03-2023', '02-03-2023']

# This dictionary can be used to map a song name to a custom string (example usage given below):
CUSTOM_MAP = {
    # 'rotting christ - chaos geneto (the sign of prime creation)': 'rotting christ - the signe of prime creation'
    'eluveitie - anu': '',
    'eluveitie - guitar solo': '',
    'eluveitie - drum solo': '',
    'eluveitie - de ruef vo de bärge / the call of the mountains': 'eluveitie - the call of the mountains',
    'eluveitie - l\'appel des montagnes': 'eluveitie - the call of the mountains',
    'omnium gatherum - unknowing': 'omnium gatherum - the unknowing'
}

REPERTORIO_TOKEN = os.getenv('REPERTORIO_TOKEN')
repertorio_api = Repertorio(REPERTORIO_TOKEN)
spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(scope='playlist-modify-public,user-read-currently-playing'))

try:
    if spotify.currently_playing()['is_playing']:
        sys.exit()
except SystemExit:  # TODO: figure out what happens when logged out
    sys.exit()
except:
    pass

playlist_tracks = []
offset = 0
while True:
    playlist_tracks_obj = spotify.playlist_items(PLAYLIST_ID, additional_types=('track',), limit=100, offset=offset)
    if not playlist_tracks_obj['items']:
        break
    for item in playlist_tracks_obj['items']:
        playlist_tracks.append(item['track']['id'])
    offset += 100

offset = 0
while offset < len(playlist_tracks):
    spotify.playlist_remove_all_occurrences_of_items(PLAYLIST_ID, playlist_tracks[offset:offset + 100])
    offset += 100

time.sleep(1)

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
            artists = repertorio_api.artists(artistName=band_name, sort='relevance')
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
                setlists = repertorio_api.setlists(artistMbid=artist_mbid, p=page_num)
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
    playlist_add_buffer = []

    for k, v in out_d.items():
        band, song = k.split(' - ', 1)
        spotify_search_query = f'{song} artist:{band}'
        success = False
        timeout_ctr = 0
        while not success:
            try:
                search_result = spotify.search(spotify_search_query, limit=5)
                success = True
            except:
                timeout_ctr += 1
                if timeout_ctr >= 50:
                    success = True  # give up
                time.sleep(.5)

        print(f'{band:>{max_band_name}} - {song:>{max_song_name}}: {v:<20} ({len(d[k]):>2})')
        try:
            song_id = search_result['tracks']['items'][0]['id']
        except (IndexError, TypeError) as e:
            print(str(e))
            continue

        playlist_add_buffer.append(song_id)

    if playlist_add_buffer:
        success = False
        timeout_ctr = 0
        while not success:
            try:
                spotify.playlist_add_items(PLAYLIST_ID, playlist_add_buffer)
                success = True
            except:
                timeout_ctr += 1
                if timeout_ctr >= 50:
                    success = True  # give up
                time.sleep(.5)

        playlist_add_buffer.clear()
        time.sleep(.5)

    print()

