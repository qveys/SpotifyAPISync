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

def get_token():
    auth_string = CLIENT_ID + ":" + CLIENT_SECRET
    auth_bytes = auth_string.encode('utf-8')
    auth_base64 = str(base64.b64encode(auth_bytes), 'utf-8')

    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": "Basic " + auth_base64,
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {"grant_type": "client_credentials"}

    try:
        result = requests.post(url, headers=headers, data=data)
        result.raise_for_status()  # Raise an HTTPError for bad responses
        json_result = result.json()
        token = json_result.get("access_token")
        if token:
            return token
        else:
            print("Token not found in response:", json_result)
    except requests.exceptions.HTTPError as errh:
        print(f"HTTP Error during token request: {errh}")
    except requests.exceptions.RequestException as err:
        print(f"Request Exception during token request: {err}")

    return None

# Attempt to get a new token
new_token = get_token()

if new_token:
    # Update the global token variable
    token = new_token
    print("Successfully obtained a new token.")
else:
    print("Failed to obtain a new token.")

# Function to get user authorization and return access token
def get_user_token(client_id, client_secret, redirect_uri):
    authorization_base_url = "https://accounts.spotify.com/authorize"
    token_url = "https://accounts.spotify.com/api/token"
    scope = "playlist-modify-public playlist-modify-private"  
    state = "123" 

    # Redirect the user to the Spotify Accounts service for authorization
    auth_url = f"{authorization_base_url}?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}&state={state}"

    print(f"Please go to this URL and authorize access: {auth_url}")
    authorization_code = input("Enter the authorization code from the redirect URI: ")

    # Use the authorization code to request an access token
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

# Update the global token variable with the user token
redirect_uri = "https://www.google.co.in/" 
user_token = get_user_token(CLIENT_ID, CLIENT_SECRET, redirect_uri)

if user_token:
    token = user_token
    print("Successfully obtained user token.")
else:
    print("Failed to obtain user token.")

def get_auth_header(token):
    return {"Authorization": "Bearer " + token}

def get_user_detials(token):
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

def countries():
    return ['world','algeria','argentina','argentina/buenos-aires', 'australia','australia/adelaide','australia/brisbane','australia/melbourne','australia/perth','australia/sydney',
             'austria','azerbaijan', 'belarus', 'belgium', 'brazil','brazil/brasília','brazil/rio-de-janeiro','brazil/s%C3%A3o-paulo', 'bulgaria','cameroon', 'canada', 'canada/calgary',
             'canada/edmonton','canada/london','canada/montr%C3%A9al','canada/ottawa','canada/qu%C3%A9bec','canada/toronto','canada/vancouver','chile','chile/santiago', 'china','china/beijing',
             'china/shanghai', 'colombia','colombia/bogot%C3%A1','colombia/medell%C3%ADn', 'costa-rica', 'croatia', 'czechia','ivory-coast', 'denmark', 'denmark/copenhagen', 'egypt',
             'finland','finland/helsinki', 'france','france/bordeaux','france/le-havre','france/lyon','france/marseille','france/montpellier','france/nantes','france/nice','france/paris'
             ,'france/strasbourg','france/toulouse', 'germany','germany/berlin', 'germany/d%C3%BCsseldorf','germany/essen','germany/frankfurt-am-main','germany/hamburg','germany/hannover','germany/k%C3%B6ln',
             'germany/mannheim','germany/munich','germany/stuttgart',  'ghana', 'greece','greece/athens', 'hungary', 'india', 'india/bengaluru','india/delhi','india/mumbai', 'indonesia',
             'ireland','ireland/dublin', 'israel','israel/tel-aviv', 'italy','italy/florence','italy/milan','italy/naples','italy/palermo','italy/rome','italy/turin','italy/venice', 'japan',
             'japan/osaka','japan/tokyo', 'kazakhstan','kenya', 'malaysia', 'mexico','mexico/guadalajara', 'mexico/mexico-city','mexico/monterrey','mexico/puebla', 'mexico/tijuana', 'mexico/toluca',
             'mozambique', 'morocco', 'netherlands','netherlands/amsterdam','netherlands/maastricht', 'netherlands/rotterdam', 'netherlands/the-hague', 'netherlands/utrecht', 'new-zealand',
             'nigeria','nigeria/benin-city', 'nigeria/kaduna', 'nigeria/kano', 'nigeria/lagos', 'nigeria/port-harcourt', 'norway', 'norway/oslo', 'peru', 'peru/lima', 'philippines','poland',
             'poland/kraków', 'poland/warsaw', 'portugal', 'portugal/lisbon','portugal/porto', 'romania', 'romania/bucharest', 'russia', 'russia/moscow', 'russia/saint-petersburg', 'saudi-arabia',
             'singapore', 'singapore/singapore', 'senegal', 'south-africa','south-africa/cape-town', 'south-africa/durban', 'south-africa/johannesburg', 'south-korea', 'south-korea/seoul',
             'spain', 'spain/barcelona', 'spain/madrid', 'spain/sevilla', 'spain/valencia', 'sweden', 'sweden/göteborg', 'sweden/malmö', 'sweden/stockholm', 'switzerland','tanzania',
             'thailand','thailand/bangkok', 'tunisia', 't%C3%BCrkiye', 't%C3%BCrkiye/adana', 't%C3%BCrkiye/ankara','t%C3%BCrkiye/istanbul', 'ukraine','ukraine/kyiv', 'united-arab-emirates',
             'united-arab-emirates/dubai', 'united-kingdom', 'united-kingdom/belfast', 'united-kingdom/birmingham', 'united-kingdom/bristol', 'united-kingdom/brighton', 'united-kingdom/cardiff',
             'united-kingdom/edinburgh', 'united-kingdom/glasgow', 'united-kingdom/leeds', 'united-kingdom/liverpool', 'united-kingdom/london', 'united-kingdom/manchester', 'united-kingdom/newcastle-upon-tyne',
             'united-kingdom/nottingham', 'united-kingdom/portsmouth', 'united-kingdom/sheffield', 'united-states', 'united-states/albany', 'united-states/atlanta', 'united-states/baltimore', 'united-states/boston',
             'united-states/buffalo', 'united-states/charlotte', 'united-states/chicago', 'united-states/cincinnati', 'united-states/cleveland','united-states/columbia', 'united-states/columbus',
             'united-states/corpus-christi', 'united-states/dallas', 'united-states/denver', 'united-states/detroit', 'united-states/el-paso', 'united-states/fresno', 'united-states/honolulu', 'united-states/houston',
             'united-states/indianapolis', 'united-states/irvine', 'united-states/jacksonville', 'united-states/kansas-city', 'united-states/las-vegas', 'united-states/long-island', 'united-states/los-angeles',
             'united-states/louisville', 'united-states/memphis', 'united-states/miami', 'united-states/minneapolis', 'united-states/nashville', 'united-states/new-haven',  'united-states/new-orleans', 'united-states/new-york-city',
             'united-states/newark', 'united-states/oklahoma-city', 'united-states/orlando', 'united-states/philadelphia', 'united-states/phoenix', 'united-states/pittsburgh', 'united-states/portland-or', 'united-states/raleigh',
             'united-states/sacramento', 'united-states/salt-lake-city', 'united-states/san-antonio', 'united-states/san-bernardino', 'united-states/san-diego', 'united-states/san-francisco', 'united-states/seattle',
             'united-states/st.-louis', 'united-states/tampa', 'united-states/virginia-beach', 'united-states/washington-d.c.', 'united-states/yonkers',
             'uruguay','uzbekistan','uzbekistan/tashkent', 'venezuela','vietnam','zambia']

def create_playlist(token, title):
    my_user_id = get_user_detials(token)["id"]
    url = f"https://api.spotify.com/v1/users/{my_user_id}/playlists"
    headers = get_auth_header(token)
    headers["Content-Type"] = "application/json"
    data = {"name": title}
    data_json = json.dumps(data)
    result = requests.post(url, headers=headers, data=data_json)

    if result.status_code == 201:  # HTTP 201 Created
        json_result = result.json()
        return json_result
    elif result.status_code == 429:  # HTTP 429 Too Many Requests
        retry_after = result.headers['Retry-After']
        print(f"Rate limit hit. Retry after {retry_after} seconds.")
        return None
    else:
        print(f"Failed to create playlist: {result.content}")
        return None

def search_the_song(token, artist_name, song_name):
    url = "https://api.spotify.com/v1/search"
    headers = get_auth_header(token)
    query = f"?q={song_name} {artist_name}&type=track&limit=1"

    query_url = url + query
    result = requests.get(query_url, headers=headers)
    json_result = json.loads(result.content)

    # Check if the request was successful and the song was found
    if result.status_code == 200 and 'tracks' in json_result and 'items' in json_result['tracks'] and json_result['tracks']['items']:
        return json_result['tracks']['items'][0]
    else:
        print(f"Song not found: {song_name} by {artist_name}")
        return None

def add_tracks_to_playlist(token, playlist_id, track_ids):
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    headers = get_auth_header(token)
    headers["Content-Type"] = "application/json"
    data = {"uris": track_ids}
    data_json = json.dumps(data)
    result = requests.post(url, headers=headers, data=data_json)

    if result.status_code == 201:  # HTTP 201 Created
        json_result = result.json()
        return json_result
    else:
        print(f"Failed to add tracks to playlist: {result.content}")
        return None


logging.basicConfig(filename='app.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')


def preexisting_playlist(token, total_playlists):
    my_user_id = get_user_detials(token)["id"]
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
    
def updating_playlist_name(token, playlist_id, title):
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}"
    headers = get_auth_header(token)
    headers["Content-Type"] = "application/json"
    data = {"name": title}
    data_json = json.dumps(data)
    result = requests.put(url, headers=headers, data=data_json)

    if result.status_code == 200:  # HTTP 200 OK
        return None
    else:
        print(f"Failed to update playlist name: {result.content}")
        return None

    
def main():
    directory = "/Users/laurent/Downloads/CSV-to-spotify-playlist/csv-to-spotify-playlist"
    total_files = len([name for name in os.listdir(directory) if name.endswith(".csv")])
    processed_files = 0
    user_input_update = input("Do you want to run the whole script or update any existing playlist? (run/update): ").lower()
    if user_input_update == "update":
        user_input_specific_input = input("Enter the absolute path of the file you want to update: ")
        filepath = user_input_specific_input
        title, _ = os.path.splitext(os.path.basename(filepath))
        title_without_date = re.sub(r'-\d{2}-\d{2}-\d{4}$', '', title)
        user_input_playlist = input("Check on your spotify id for the total no of playlists and enter the total no of playlists: ")
        playlists_concern = preexisting_playlist(token, int(user_input_playlist))
        for name in playlists_concern:
            if name.startswith(title_without_date):
                print(f"Playlist with the name {name} already exists")
                print(f'Processing file: {filepath} ({processed_files}/{total_files})')
                print(f'Title: {title}')
                playlist_id = playlists_concern[name]
                updating_playlist_name(token, playlist_id, title)
                break
            else:
                continue
        else:
            print(f'Processing file: {filepath} ({processed_files}/{total_files})')
            print(f'Title: {title}')
            playlist = create_playlist(token, title)
            playlist_id = playlist["id"]
        with open(filepath, 'r') as file:
            csv_reader = csv.reader(file)
            next(csv_reader)
            next(csv_reader)
            next(csv_reader)
            total_songs = sum(1 for row in csv.reader(open(filepath))) - 3
            processed_songs = 0
            for row in csv_reader:
                print(f'artist: {row[1]}')
                print(f'track: {row[0]}')
                artist_name = row[1]
                track_name = row[0]
                track = search_the_song(token, artist_name, track_name)
                if track:
                    track_id = track["uri"]
                    add_tracks_to_playlist(token, playlist_id, [track_id])
                else:
                    logging.warning(f'This track not found hence not being added to playlist: {track_name} by {artist_name} in file: {filepath}')
                processed_songs += 1
                print(f'Adding {track_name} by {artist_name} ({processed_songs}/{total_songs} {processed_songs/total_songs*100:.2f}%)')
                continue
            return None
    
    else:
        for filename in os.listdir(directory):
            if filename.endswith(".csv"):
                processed_files += 1
                filepath = os.path.join(directory, filename)
                title, _ = os.path.splitext(os.path.basename(filepath))
                title_without_date = re.sub(r'-\d{2}-\d{2}-\d{4}$', '', title)
                user_input_playlist = input("Check on your spotify id for the total no of playlists and enter the total no of playlists: ")
                playlists_concern = preexisting_playlist(token, int(user_input_playlist))
                for name in playlists_concern:
                    if name.startswith(title_without_date):
                        print(f"Playlist with the name {name} already exists")
                        print(f'Processing file: {filename} ({processed_files}/{total_files})')
                        print(f'Title: {title}')
                        playlist_id = playlists_concern[name]
                        updating_playlist_name(token, playlist_id, title)
                        break
                    else:
                        continue
                else:
                    print(f'Processing file: {filename} ({processed_files}/{total_files})')
                    print(f'Title: {title}')
                    playlist = create_playlist(token, title)
                    playlist_id = playlist["id"]
                with open(filepath, 'r') as file:
                    csv_reader = csv.reader(file)
                    next(csv_reader)  # Skip the title
                    next(csv_reader)  # Skip the date
                    next(csv_reader)  # Skip the header
                    total_songs = sum(1 for row in csv.reader(open(filepath))) - 3  # Subtract 3 for the skipped rows
                    processed_songs = 0

                    for row in csv_reader:
                        print(f'artist: {row[1]}')
                        print(f'track: {row[0]}')
                        artist_name = row[1]
                        track_name = row[0]
                        track = search_the_song(token, artist_name, track_name)
                        if track:
                            track_id = track["uri"]
                            add_tracks_to_playlist(token, playlist_id, [track_id])
                        else:
                            logging.warning(f'This track not found hence not being added to playlist: {track_name} by {artist_name} in file: {filename}')
                        processed_songs += 1
                        print(f'Adding {track_name} by {artist_name} ({processed_songs}/{total_songs} {processed_songs/total_songs*100:.2f}%) in file: {filename} ({processed_files}/{total_files})')
                        continue


if __name__ == "__main__":
    main()
