# --- Imports ---
import os
import time
import base64
import requests
import json
import csv
import re
import logging
from pathlib import Path
from dotenv import load_dotenv
import concurrent.futures

# --- Config / Setup ---
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
load_dotenv()
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

# --- Utilitaires génériques ---
def http_request(method, url, headers=None, data=None, params=None, max_retries=3, timeout=10):
    for attempt in range(1, max_retries + 1):
        try:
            if method == 'GET':
                resp = requests.get(url, headers=headers, params=params, timeout=timeout)
            elif method == 'POST':
                resp = requests.post(url, headers=headers, data=data, params=params, timeout=timeout)
            elif method == 'PUT':
                resp = requests.put(url, headers=headers, data=data, params=params, timeout=timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Gestion du rate limit Spotify (429)
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", "5"))
                print(f"\n")
                logging.warning(f"Rate limited by Spotify (429). Waiting {retry_after} seconds before retrying...")
                time.sleep(3 ** retry_after)
                continue
            if resp.status_code >= 500:
                logging.warning(f"HTTP {resp.status_code} on {url}, retrying ({attempt}/{max_retries})...")
                time.sleep(2 ** attempt)
                continue
            return resp
        except requests.RequestException as e:
            logging.warning(f"Request error: {e}, retrying ({attempt}/{max_retries})...")
            time.sleep(2 ** attempt)
    logging.error(f"Failed to {method} {url} after {max_retries} attempts.")
    raise RuntimeError(f"HTTP request failed: {method} {url}")

def update_env_refresh_token(refresh_token, path=None):
    if path is None:
        base_dir = Path(__file__).parent
        path = base_dir / ".env"
    lines = []
    found = False
    if Path(path).exists():
        with open(path, "r") as f:
            for line in f:
                if line.startswith("REFRESH_TOKEN="):
                    lines.append(f"REFRESH_TOKEN={refresh_token}\n")
                    found = True
                else:
                    lines.append(line)
    if not found:
        lines.append(f"REFRESH_TOKEN={refresh_token}\n")
    with open(path, "w") as f:
        f.writelines(lines)
    logging.info(f"REFRESH_TOKEN updated in {path}")

# --- Spotify API Wrappers ---
def get_user_token(client_id, client_secret, redirect_uri):
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
        result = http_request('POST', token_url, headers=headers, data=data)
        result.raise_for_status()
        json_result = result.json()
        user_token = json_result.get("access_token")
        refresh_token = json_result.get("refresh_token")
        if not user_token:
            logging.error(f"User Token not found in response: {json_result}")
            raise RuntimeError("No access_token in Spotify response")
        return user_token, refresh_token
    except requests.exceptions.HTTPError as errh:
        logging.error(f"HTTP Error during user token request: {errh}")
        raise
    except requests.exceptions.RequestException as err:
        logging.error(f"Request Exception during user token request: {err}")
        raise

def get_token_with_refresh(client_id, client_secret, refresh_token):
    token_url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": "Basic " + base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("utf-8"),
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    result = http_request('POST', token_url, headers=headers, data=data)
    result.raise_for_status()
    json_result = result.json()
    return json_result.get("access_token"), json_result.get("refresh_token", refresh_token)

def get_auth_header(token):
    return {"Authorization": f"Bearer {token}"}

def get_user_details(token):
    url = "https://api.spotify.com/v1/me"
    headers = get_auth_header(token)
    result = http_request('GET', url, headers=headers)
    try:
        json_result = result.json()
    except ValueError:
        raise Exception("Invalid response from Spotify API")
    if result.status_code != 200:
        raise Exception(f"Spotify API error: {json_result.get('error', {}).get('message', 'Unknown error')}")
    if "id" not in json_result:
        raise KeyError("The 'id' key is missing in the response from Spotify. Response: " + str(json_result))
    return json_result

# --- Fonctions métier ---
def get_all_playlists_with_tracks(token):
    user_id = get_user_details(token)["id"]
    limit = 50
    offset = 0
    playlists = {}
    while True:
        url = f"https://api.spotify.com/v1/users/{user_id}/playlists?limit={limit}&offset={offset}"
        headers = get_auth_header(token)
        resp = http_request('GET', url, headers=headers)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        if not items:
            break
        for playlist in items:
            playlists[playlist["name"]] = {
                "id": playlist["id"],
                "track_ids": set()
            }
        offset += limit
    for name, info in playlists.items():
        pid = info["id"]
        track_ids = set()
        t_limit = 100
        t_offset = 0
        while True:
            url = f"https://api.spotify.com/v1/playlists/{pid}/tracks?fields=items.track.id,total,next&limit={t_limit}&offset={t_offset}"
            headers = get_auth_header(token)
            resp = http_request('GET', url, headers=headers)
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

def create_playlist(token, name, public=True, processed_playlists=None, total_playlists=None):
    user_id = get_user_details(token)["id"]
    url = f"https://api.spotify.com/v1/users/{user_id}/playlists"
    headers = get_auth_header(token)
    headers["Content-Type"] = "application/json"
    data = json.dumps({"name": name, "public": public})
    response = http_request('POST', url, headers=headers, data=data)
    if response.status_code != 201:
        logging.error(f"Failed to create playlist '{name}': {response.text}")
        raise RuntimeError(f"Spotify API error: {response.text}")
    if processed_playlists is not None and total_playlists is not None:
        logging.info(f"({processed_playlists}/{total_playlists} {processed_playlists/total_playlists*100:.2f}%) > Created new playlist '{name}'")
    else:
        logging.info(f"Created new playlist '{name}'")
    return response.json()

def updating_playlist_name(token, playlist_id, new_name):
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}"
    headers = get_auth_header(token)
    headers["Content-Type"] = "application/json"
    data = json.dumps({"name": new_name})
    response = http_request('PUT', url, headers=headers, data=data)
    if response.status_code not in (200, 201):
        logging.warning(f"Failed to update playlist name: {response.text}")
    else:
        logging.info(f"Renamed playlist to '{new_name}' (id: {playlist_id})")

def search_the_song(token, artist_name, track_name):
    query = f"track:{track_name} artist:{artist_name}"
    url = f"https://api.spotify.com/v1/search?q={requests.utils.quote(query)}&type=track&limit=1"
    headers = get_auth_header(token)
    result = http_request('GET', url, headers=headers)
    json_result = result.json()
    tracks = json_result.get("tracks", {}).get("items")
    if tracks:
        return tracks[0]
    return None

def add_tracks_to_playlist_batch(token, playlist_id, track_uris, processed_songs=None, total_songs=None):
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    headers = get_auth_header(token)
    headers["Content-Type"] = "application/json"
    for i in range(0, len(track_uris), 100):
        batch = track_uris[i:i+100]
        data = json.dumps({"uris": batch})
        response = http_request('POST', url, headers=headers, data=data)
        if response.status_code not in (200, 201):
            logging.warning(f"Failed to add tracks to playlist: {response.text}")
        else:
            if processed_songs is not None and total_songs is not None:
                logging.info(f"({processed_songs}/{total_songs} {processed_songs/total_songs*100:.2f}%) > Added {len(batch)} tracks to playlist (id: {playlist_id})")
            else:
                logging.info(f"Added {len(batch)} tracks to playlist (id: {playlist_id})")

# --- Stats class ---
class Stats:
    def __init__(self):
        self.playlists_created = 0
        self.playlists_updated = 0
        self.tracks_added = 0
        self.tracks_already_present = 0
        self.tracks_not_found = 0
        self.files_skipped = 0
    def print_summary(self):
        print("\n")
        print("\n--- Résumé de la synchronisation Spotify ---")
        print(f"Playlists créées : {self.playlists_created}")
        print(f"Playlists renommées : {self.playlists_updated}")
        print(f"Tracks ajoutés : {self.tracks_added}")
        print(f"Tracks déjà présents : {self.tracks_already_present}")
        print(f"Tracks non trouvés : {self.tracks_not_found}")
        print(f"Fichiers CSV ignorés (playlist déjà complète) : {self.files_skipped}")
        print("-------------------------------------------\n")

# --- Traitement principal d'un fichier CSV ---
def process_file(token, playlists_concern, csv_path: Path, stats: 'Stats', processed_files=None, total_files=None):
    title = csv_path.stem
    title_without_date = re.sub(r'-\d{2}-\d{2}-\d{4}$', '', title)
    if processed_files is not None and total_files is not None:
        logging.info(f"({processed_files}/{total_files} {processed_files/total_files*100:.2f}%) > Processing file: {csv_path.name} | Title: {title}")
    else:
        logging.info(f"Processing file: {csv_path.name} | Title: {title}")
    playlist_id = None
    track_ids_set = set()
    playlist_found = False
    for name, info in playlists_concern.items():
        if name.startswith(title_without_date):
            playlist_id = info["id"]
            track_ids_set = info["track_ids"]
            playlist_found = True
            if name != title_without_date:
                updating_playlist_name(token, playlist_id, title_without_date)
                stats.playlists_updated += 1
            break
    if not playlist_found:
        playlist = create_playlist(token, title_without_date)
        playlist_id = playlist["id"]
        track_ids_set = set()
        playlists_concern[title_without_date] = {"id": playlist_id, "track_ids": track_ids_set}
        stats.playlists_created += 1
    with csv_path.open('r') as file:
        csv_reader = list(csv.reader(file))
        lines = csv_reader[3:]
        total_songs = len(lines)
        if len(track_ids_set) >= total_songs:
            logging.info(f"Playlist '{title_without_date}' already has {len(track_ids_set)} tracks (CSV: {total_songs}), skipping.\n\n")
            stats.files_skipped += 1
            return
        search_args = [(token, row[1], row[0]) for row in lines]
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            future_to_idx = {executor.submit(search_the_song, *args): idx for idx, args in enumerate(search_args)}
            results = [None] * len(lines)
            for future in concurrent.futures.as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result()
                except Exception as exc:
                    results[idx] = None
                    logging.warning(f"Track search failed at line {idx+4} in {csv_path.name}: {exc}")
        to_add_uris = []
        processed_songs = 0
        for idx, (row, track) in enumerate(zip(lines, results), 1):
            artist_name = row[1]
            track_name = row[0]
            if track:
                if track["id"] not in track_ids_set:
                    to_add_uris.append(track["uri"])
                    track_ids_set.add(track["id"])
                    stats.tracks_added += 1
                    processed_songs += 1
                    logging.info(f"({processed_songs}/{total_songs} {processed_songs/total_songs*100:.2f}%) >Track to add: {track_name} by {artist_name}")
                else:
                    stats.tracks_already_present += 1
            else:
                logging.warning(f"Not found: {track_name} by {artist_name} in file: {csv_path.name}")
                stats.tracks_not_found += 1
        if to_add_uris:
            add_tracks_to_playlist_batch(token, playlist_id, to_add_uris, processed_songs=processed_songs, total_songs=total_songs)
        else:
            logging.info(f"No new tracks to add for playlist '{title_without_date}'")

# --- Orchestration globale ---
def main():
    directory = Path("/Users/laurent/Downloads/CSV-to-spotify-playlist/csv-to-spotify-playlist")
    csv_files = list(directory.glob("*.csv"))
    redirect_uri = "https://www.google.co.in/"
    refresh_token = os.getenv("REFRESH_TOKEN")
    token = None
    new_refresh_token = None
    if refresh_token:
        try:
            token, new_refresh_token = get_token_with_refresh(CLIENT_ID, CLIENT_SECRET, refresh_token)
            logging.info("Obtained access_token via refresh_token.")
            if new_refresh_token and new_refresh_token != refresh_token:
                update_env_refresh_token(new_refresh_token)
        except Exception as e:
            logging.warning(f"Refresh token failed: {e}. Falling back to manual authorization.")
    if not token:
        token, new_refresh_token = get_user_token(CLIENT_ID, CLIENT_SECRET, redirect_uri)
        if new_refresh_token:
            update_env_refresh_token(new_refresh_token)
    if not token:
        logging.error("❌ Failed to obtain a valid user token. Exiting.")
        return
    playlists_concern = get_all_playlists_with_tracks(token)
    stats = Stats()
    total_files = len(csv_files)
    for processed_files, csv_path in enumerate(csv_files, 1):
        process_file(token, playlists_concern, csv_path, stats, processed_files=processed_files, total_files=total_files)
    stats.print_summary()

# --- Point d'entrée ---
if __name__ == "__main__":
    main()
