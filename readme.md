# SpotifyFutureSetlistGenerator
This script creates a Spotify playlist that consists of future potential playlists of bands specified by the user.
Data about songs played by a band is gathered from setlist.fm

The user has to set the environment variables `SPOTIPY_CLIENT_ID`, `SPOTIPY_CLIENT_SECRET`, `SPOTIPY_REDIRECT_URI`, and
`REPERTORIO_TOKEN` so that the script can communicate with the Spotify and setlist.fm APIs. Instructions on how to set
these can be found on:
* https://spotipy.readthedocs.io/en/2.22.1/#authorization-code-flow
* https://repertorio.readthedocs.io/en/latest/