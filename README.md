# CSV-to-spotify-playlist

## Overview

Spotify Playlist Creator is a Python script that enables the creation of Spotify playlists from a CSV file containing a list of songs. The script interacts with the Spotify API to authenticate and obtain the necessary tokens for playlist creation and song search.

## Features

- **Token Management:** The script handles the retrieval and management of Spotify API tokens for both client and user authorization.
  
- **User Authorization:** Allows users to authorize the script to access their Spotify account for playlist creation.

- **Playlist Creation:** Creates a new playlist on the user's Spotify account based on the CSV file's title.

- **Song Search:** Searches for each song in the CSV file and adds the found tracks to the created playlist.

- **Logging:** Logs any issues or warnings encountered during the process to the `app.log` file.

## Prerequisites

- Python 3.x
- Required Python packages: `requests`

## Installation

1. Clone the repository to your local machine:

    ```bash
    git clone https://github.com/5rijan/CSV-to-spotify-playlist.git
    ```

2. Navigate to the project directory:

    ```bash
    cd CSV-to-spotify-playlist
    ```

3. Install the required Python packages:

    ```bash
    pip install -r requirements.txt
    ```

## Usage

1. Obtain your Spotify API credentials (CLIENT_ID and CLIENT_SECRET) and set them as environment variables in a `.env` file:

    ```env
    CLIENT_ID=your_client_id
    CLIENT_SECRET=your_client_secret
    ```

2. Run the script to authenticate and obtain the necessary tokens:

    ```bash
    python script.py
    ```

3. Follow the prompted instructions to authorize access and obtain the user token.

4. Place your CSV file with the list of songs in the "csv files" directory. The CSV file should have columns: "Title," "Artist," and "Track Name."

5. Run the script again to create a new playlist and add the songs from the CSV file to it:

    ```bash
    python script.py
    ```

## Logging

Any issues or warnings encountered during the process will be logged in the `app.log` file.

## Contributing

Feel free to contribute to this project by submitting issues or pull requests. Your contributions are welcome and appreciated.

## License

This project is licensed under the [MIT License](LICENSE).

## Author

Srijan Chaudhary (5rijan)
