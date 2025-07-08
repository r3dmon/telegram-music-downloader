# Telegram Music Downloader

> **Note:** This project was developed with AI assistance.

A Python-based application designed to download audio files (primarily music) from specified Telegram channels. It offers features like advanced filtering, download tracking, and robust logging.

## Features

*   **Download from Telegram**: Fetches audio files from public or private Telegram channels you have access to.
*   **Advanced Filtering**:
    *   Filter by file type (e.g., audio, document).
    *   Filter by specific file formats (e.g., `.mp3`, `.flac`, `.wav`).
    *   Filter by file size (min/max MB).
    *   Filter by message date range.
*   **Download & Message Tracking**: Tracks both downloaded files and processed messages using separate, robust tracker modules. Prevents duplicates and enables reliable recovery.
*   **Robust Logging**: Comprehensive and resilient logging to both console and file, including log rotation and logger health checks.
*   **Customizable File Naming**: Define templates for naming downloaded files.
*   **Track Name Normalization & Cleanup**: Automatically cleans up and standardizes track names after download (optional, see below).
*   **Secure Configuration**:
    *   Main application settings are managed in `src/config.yaml`.

### Track Name Normalization & Cleanup

The downloader can automatically clean and standardize the names of downloaded audio tracks. This feature removes unnecessary tags, extra spaces, technical info, and other "garbage" from file names, making your downloaded music tidy and consistent.

- **How it works:**
    - Applies a series of normalization functions to each file name after download (removes message IDs, extra spaces, bracket artifacts, technical tags, etc).
    - Helps prevent messy or unreadable filenames from Telegram uploads.
- **How to enable:**
    - In your `src/config.yaml` or `src/local_config.yaml`, set:
      ```yaml
      normalize_track_names: true
      ```
    - By default, this feature is **disabled** (`false`).
- **When enabled:**
    - All normalization and cleanup rules are applied automatically to every downloaded track.
    - If disabled, file names are left as-is.

## Setup

1. **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/telegram-music-downloader.git
    cd telegram-music-downloader
    ```

2. **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3. **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4. **Configure the application:**
    - Edit `src/config.yaml` for main settings (channels, filters, download directory, etc).
    - Create `src/local_config.yaml` and add your Telegram `api_id` and `api_hash` (and optionally `phone_number`).
      Example `src/local_config.yaml`:
      ```yaml
      telegram:
        api_id: 1234567
        api_hash: "your_api_hash_here"
        # phone_number: "+1234567890" # If needed for login
      ```

### How to Get Channel or Group ID

To specify channels in `config.yaml`, you need their numeric IDs. Here's how to get them:

1. Forward any message from the target channel to @ShowJsonBot
2. The bot will reply with JSON data containing channel information
3. Look for `"chat":{"id":-1001234567890}` in the response
4. Use the number after `"id":` (including the minus sign)

**Important Notes:**
- Channel IDs are usually negative numbers (e.g., `-1001234567890`)
- Public channels can be specified by username (e.g., `@channelname`) or numeric ID
- Private channels/groups must use numeric ID
- In `config.yaml`, list channel IDs under the `channels:` section:
  ```yaml
  channels:
    - -1001234567890  # Private channel ID
    - @publicchannel  # Public channel username
    - -1009876543210  # Another channel ID
  ```

## Usage

- Run the main script from the project's root directory:
    ```bash
    python src/main.py
    ```
- To use a custom config file:
    ```bash
    python src/main.py --config path/to/your/custom_config.yaml
    ```

- The application will automatically manage sessions, track downloads and messages, and log all activity. Statistics are available after each run.

## Project Structure

```
telegram-music-downloader/
├── .gitignore
├── README.md
├── requirements.txt
├── src/
│   ├── main.py               # Async main entry point
│   ├── config.yaml           # Main configuration file (template/defaults)
│   ├── local_config.yaml     # Local configuration with secrets (gitignored)
│   ├── config_loader.py      # Loads and merges configurations
│   ├── client.py             # Async Telegram client setup
│   ├── downloader.py         # Async file downloading logic
│   ├── logger.py             # Robust logging (rotation, health checks)
│   ├── media_filter.py       # Flexible, configurable media filtering
│   ├── message_parser.py     # Async parsing of channel messages for media
│   ├── session_manager.py    # Manages and backs up Telegram sessions
│   └── tracker.py            # Tracks downloaded files and processed messages
└── data/                     # Default directory for downloads, logs, sessions
    ├── downloads/
    ├── logs/
    └── sessions/
```

## Requirements

- Python 3.9+
- [Telethon](https://github.com/LonamiWebs/Telethon) and other dependencies in `requirements.txt`

## License

MIT
