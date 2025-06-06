from pathlib import Path
import logging
import os
import base64
import requests
import json
import csv
from dotenv import load_dotenv
import re

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

# Load environment variables
load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

# Fonction pour obtenir un token d'utilisateur avec authentification OAuth
def get_user_token(client_id, client_secret, redirect_uri):
    """Obtain a user token via OAuth. Logs URL, expects code from user."""
    authorization_base_url = "https://accounts.spotify.com/authorize"
    token_url = "https://accounts.spotify.com/api/token"
    scope = "playlist-modify-public playlist-modify-private"
    state = "123"

    auth_url = (
        f"{authorization_base_url}?response_type=code&client_id={client_id}"
        f"&redirect_uri={redirect_uri}&scope={scope}&state={state}"
    )
    logging.info(f"Go to this URL and authorize access: {auth_url}")
    authorization_code = input("Enter the authorization code from the redirect URI: ").strip()

    headers = {
        "Authorization": "Basic " + base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("utf-8"),
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "authorization_code",
        "code": authorization_code,
        "redirect_uri": redirect_uri
    }
    try:
        result = requests.post(token_url, headers=headers, data=data)
        result.raise_for_status()
        json_result = result.json()
        user_token = json_result.get("access_token")
        if not user_token:
            logging.error(f"User Token not found in response: {json_result}")
            raise RuntimeError("No access_token in Spotify response")
        return user_token
    except requests.exceptions.HTTPError as errh:
        logging.error(f"HTTP Error during user token request: {errh}")
        raise
    except requests.exceptions.RequestException as err:
        logging.error(f"Request Exception during user token request: {err}")
        raise

def get_auth_header(token):
    return {"Authorization": f"Bearer {token}"}

def get_user_details(token):
    url = "https://api.spotify.com/v1/me"
    headers = get_auth_header(token)
    result = requests.get(url, headers=headers)

    try:
        json_result = result.json()
    except ValueError:
        raise Exception("Invalid response from Spotify API")

    if result.status_code != 200:
        raise Exception(f"Spotify API error: {json_result.get('error', {}).get('message', 'Unknown error')}")

    if "id" not in json_result:
        raise KeyError("The 'id' key is missing in the response from Spotify. Response: " + str(json_result))

    return json_result

def get_all_playlists_with_tracks(token):
    """Retourne {playlist_name: {'id': ..., 'track_ids': set([...])}}"""
    user_id = get_user_details(token)["id"]
    limit = 50
    offset = 0
    playlists = {}

    # Récupère toutes les playlists
    while True:
        url = f"https://api.spotify.com/v1/users/{user_id}/playlists?limit={limit}&offset={offset}"
        headers = get_auth_header(token)
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        if not items:
            break
        for playlist in items:
            playlists[playlist["name"]] = {
                "id": playlist["id"],
                "track_ids": set()  # On remplit après
            }
        offset += limit

    # Pour chaque playlist, récupère tous les track IDs (pagination)
    for name, info in playlists.items():
        pid = info["id"]
        track_ids = set()
        t_limit = 100
        t_offset = 0
        while True:
            url = f"https://api.spotify.com/v1/playlists/{pid}/tracks?fields=items.track.id,total,next&limit={t_limit}&offset={t_offset}"
            headers = get_auth_header(token)
            resp = requests.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", [])
            for item in items:
                tid = item.get("track", {}).get("id")
                if tid:
                    track_ids.add(tid)
            if not data.get("next"):
                break
            t_offset += t_limit
        playlists[name]["track_ids"] = track_ids

    return playlists

def create_playlist(token, name, public=True):
    user_id = get_user_details(token)["id"]
    url = f"https://api.spotify.com/v1/users/{user_id}/playlists"
    headers = get_auth_header(token)
    headers["Content-Type"] = "application/json"
    data = json.dumps({"name": name, "public": public})
    response = requests.post(url, headers=headers, data=data)
    if response.status_code != 201:
        logging.error(f"Failed to create playlist '{name}': {response.text}")
        raise RuntimeError(f"Spotify API error: {response.text}")
    return response.json()

def get_tracks_from_playlist(token, playlist_id):
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    headers = get_auth_header(token)
    result = requests.get(url, headers=headers)
    if result.status_code != 200:
        logging.error(f"Failed to fetch tracks for playlist {playlist_id}: {result.text}")
        return []
    json_result = result.json()
    items = json_result.get("items", [])
    track_ids = [track.get("track", {}).get("id") for track in items if track.get("track")]
    return track_ids

def add_tracks_to_playlist(token, playlist_id, track_uris):
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    headers = get_auth_header(token)
    headers["Content-Type"] = "application/json"
    data = json.dumps({"uris": track_uris})
    response = requests.post(url, headers=headers, data=data)
    if response.status_code not in (200, 201):
        logging.warning(f"Failed to add tracks to playlist: {response.text}")

def search_the_song(token, artist_name, track_name):
    query = f"track:{track_name} artist:{artist_name}"
    url = f"https://api.spotify.com/v1/search?q={requests.utils.quote(query)}&type=track&limit=1"
    headers = get_auth_header(token)
    result = requests.get(url, headers=headers)
    json_result = result.json()
    tracks = json_result.get("tracks", {}).get("items")
    if tracks:
        return tracks[0]
    return None

def updating_playlist_name(token, playlist_id, new_name):
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}"
    headers = get_auth_header(token)
    headers["Content-Type"] = "application/json"
    data = json.dumps({"name": new_name})
    response = requests.put(url, headers=headers, data=data)
    if response.status_code not in (200, 201):
        logging.warning(f"Failed to update playlist name: {response.text}")

def process_file(token, playlists_concern, csv_path: Path):
    title = csv_path.stem
    title_without_date = re.sub(r'-\d{2}-\d{2}-\d{4}$', '', title)
    logging.info(f"Processing file: {csv_path.name} | Title: {title}")

    playlist_id = None
    track_ids_set = set()
    for name, info in playlists_concern.items():
        if name.startswith(title_without_date):
            logging.info(f"Playlist '{name}' already exists. Updating name to '{title_without_date}' if needed.")
            playlist_id = info["id"]
            track_ids_set = info["track_ids"]
            updating_playlist_name(token, playlist_id, title_without_date)
            break
    else:
        playlist = create_playlist(token, title_without_date)
        playlist_id = playlist["id"]
        track_ids_set = set()
        playlists_concern[title_without_date] = {"id": playlist_id, "track_ids": track_ids_set}
        logging.info(f"Created new playlist '{title_without_date}' (id: {playlist_id})")

    with csv_path.open('r') as file:
        csv_reader = list(csv.reader(file))
        lines = csv_reader[3:]
        total_songs = len(lines)
        # Si playlist existe déjà et a assez de tracks, skip
        if len(track_ids_set) >= total_songs:
            logging.info(f"Playlist '{title_without_date}' already has {len(track_ids_set)} tracks (CSV: {total_songs}), skipping.")
            return
        for idx, row in enumerate(lines, 1):
            artist_name = row[1]
            track_name = row[0]
            track = search_the_song(token, artist_name, track_name)
            if track:
                if track["id"] not in track_ids_set:
                    add_tracks_to_playlist(token, playlist_id, [track["uri"]])
                    track_ids_set.add(track["id"])
                    logging.info(f"Added: {track_name} by {artist_name} ({idx}/{total_songs})")
                else:
                    logging.info(f"Already in playlist: {track_name} by {artist_name} ({idx}/{total_songs})")
            else:
                logging.warning(f"Not found: {track_name} by {artist_name} in file: {csv_path.name}")

def main():
    directory = Path("/Users/laurent/Downloads/CSV-to-spotify-playlist/csv-to-spotify-playlist")
    csv_files = list(directory.glob("*.csv"))
    user_input_update = input("Do you want to run the whole script or update any existing playlist? (run/update): ").lower()

    redirect_uri = "https://www.google.co.in/"
    token = get_user_token(CLIENT_ID, CLIENT_SECRET, redirect_uri)
    if not token:
        logging.error("❌ Failed to obtain a valid user token. Exiting.")
        return

    playlists_concern = get_all_playlists_with_tracks(token)

    if user_input_update == "update":
        filepath = input("Enter the absolute path of the file you want to update: ")
        csv_path = Path(filepath)
        process_file(token, playlists_concern, csv_path)
    else:
        for csv_path in csv_files:
            process_file(token, playlists_concern, csv_path)

if __name__ == "__main__":
    main()
