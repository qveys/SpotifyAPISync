from dotenv import load_dotenv
import os
import base64
import requests
import json
import csv
import re
import logging

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

# Fonction pour obtenir un token d'utilisateur avec authentification OAuth
def get_user_token(client_id, client_secret, redirect_uri):
    authorization_base_url = "https://accounts.spotify.com/authorize"
    token_url = "https://accounts.spotify.com/api/token"
    scope = "playlist-modify-public playlist-modify-private"
    state = "123"

    auth_url = f"{authorization_base_url}?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}&state={state}"

    print(f"Please go to this URL and authorize access: {auth_url}")
    authorization_code = input("Enter the authorization code from the redirect URI: ")

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
        if user_token:
            return user_token
        else:
            print("User Token not found in response:", json_result)
    except requests.exceptions.HTTPError as errh:
        print(f"HTTP Error during user token request: {errh}")
    except requests.exceptions.RequestException as err:
        print(f"Request Exception during user token request: {err}")

    return None

def get_auth_header(token):
    return {"Authorization": "Bearer " + token}

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

def get_initial_playlists(token):
    user_input_playlist = input("Check on your Spotify ID for the total number of playlists and enter the total number of playlists: ")
    return preexisting_playlist(token, int(user_input_playlist))

def preexisting_playlist(token, total_playlists):
    my_user_id = get_user_details(token)["id"]
    limit = 50
    offset = 0
    playlists_concern = {}
    while offset < total_playlists:
        url = f"https://api.spotify.com/v1/users/{my_user_id}/playlists?limit={limit}&offset={offset}"
        headers = get_auth_header(token)
        result = requests.get(url, headers=headers)
        json_result = result.json()
        playlists = json_result["items"]
        for playlist in playlists:
            playlist_name = playlist["name"]
            playlists_concern[playlist_name] = playlist["id"]
        offset += limit
    return playlists_concern

def create_playlist(token, name):
    user_id = get_user_details(token)["id"]
    url = f"https://api.spotify.com/v1/users/{user_id}/playlists"
    headers = get_auth_header(token)
    headers["Content-Type"] = "application/json"
    data = json.dumps({"name": name, "public": True})
    response = requests.post(url, headers=headers, data=data)
    return response.json()

def get_tracks_from_playlist(token, playlist_id):
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    headers = get_auth_header(token)
    result = requests.get(url, headers=headers)
    json_result = result.json()
    items = json_result.get("items")
    track_ids = []
    for playlist_track in items:
      track_ids.append(playlist_track.get("track", {}).get('id'))
    return track_ids
  
def add_tracks_to_playlist(token, playlist_id, track_ids):
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    headers = get_auth_header(token)
    headers["Content-Type"] = "application/json"
    data = json.dumps({"uris": track_ids})
    requests.post(url, headers=headers, data=data)

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
    requests.put(url, headers=headers, data=data)

def main():
    global playlists_concern
    directory = "/Users/laurent/Downloads/CSV-to-spotify-playlist/csv-to-spotify-playlist"
    csv_files = [name for name in os.listdir(directory) if name.endswith(".csv")]
    total_files = len(csv_files)
    processed_files = 0
    user_input_update = input("Do you want to run the whole script or update any existing playlist? (run/update): ").lower()

    redirect_uri = "https://www.google.co.in/"
    token = get_user_token(CLIENT_ID, CLIENT_SECRET, redirect_uri)
    playlists_concern = get_initial_playlists(token)

    def process_file(filepath, filename):
        nonlocal processed_files
        title, _ = os.path.splitext(os.path.basename(filepath))
        title_without_date = re.sub(r'-\d{2}-\d{2}-\d{4}$', '', title)

        print(' ')
        print(f'Processing file: {filename} ({processed_files + 1}/{total_files} {processed_files+1/total_files*100:.2f}%)')
        print(f'Title: {title}')

        for name in playlists_concern:
            if name.startswith(title_without_date):
                print(f"Playlist with the name {name} already exists")
                playlist_id = playlists_concern[name]
                updating_playlist_name(token, playlist_id, title_without_date)
                break
        else:
            playlist = create_playlist(token, title_without_date)
            playlist_id = playlist["id"]

        track_ids_inside = get_tracks_from_playlist(token, playlist_id)
      
        with open(filepath, 'r') as file:
            csv_reader = list(csv.reader(file))
            lines = csv_reader[3:]
            total_songs = len(lines)
            processed_songs = 0
            for row in lines:
                print(' ')
                print(f'artist: {row[1]}')
                print(f'track: {row[0]}')
                artist_name = row[1]
                track_name = row[0]
                track = search_the_song(token, artist_name, track_name)
                processed_songs += 1
                if track:
                  if track["id"] not in track_ids_inside:
                    add_tracks_to_playlist(token, playlist_id, [track["uri"]])
                    print(f'Adding {track_name} by {artist_name} ({processed_songs}/{total_songs} {processed_songs/total_songs*100:.2f}%)')                    
                  else:
                    print(f'This track already inside the playlist: {track_name} by {artist_name} ({processed_songs}/{total_songs} {processed_songs/total_songs*100:.2f}%)')
                else:
                    logging.warning(f'This track not found hence not being added to playlist: {track_name} by {artist_name} in file: {filename}')
                print(' ')

        processed_files += 1

    if user_input_update == "update":
        filepath = input("Enter the absolute path of the file you want to update: ")
        filename = os.path.basename(filepath)
        process_file(filepath, filename)
    else:
        for filename in csv_files:
            filepath = os.path.join(directory, filename)
            process_file(filepath, filename)

if __name__ == "__main__":
    main()
