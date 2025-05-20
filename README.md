# Telegram Music Downloader

A Python-based application designed to download audio files (primarily music) from specified Telegram channels. It offers features like advanced filtering, download tracking, and robust logging.

## Features

*   **Download from Telegram**: Fetches audio files from public or private Telegram channels you have access to.
*   **Advanced Filtering**:
    *   Filter by file type (e.g., audio, document).
    *   Filter by specific file formats (e.g., `.mp3`, `.flac`, `.wav`).
    *   Filter by file size (min/max MB).
    *   Filter by message date range.
*   **Download Tracking**: Keeps track of successfully downloaded files to prevent duplicates (details depend on `tracker.py` implementation).
*   **Robust Logging**: Comprehensive logging to both console and file, with log rotation and health checks for the logger.
*   **Customizable File Naming**: Define templates for naming downloaded files.
*   **Secure Configuration**:
    *   Main application settings are managed in `src/config.yaml`.
    *   Sensitive credentials (like Telegram API ID and Hash) are intended to be stored in `src/local_config.yaml`, which is excluded from version control by `.gitignore`.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone telegram-music-downloader
    cd telegram-music-downloader

    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure the application:**
    *   Rename or copy `src/config.yaml` (if it contains example values) or edit it.
    *   Create `src/local_config.yaml` and add your Telegram `api_id` and `api_hash`.
        Example `src/local_config.yaml`:
        ```yaml
        telegram:
          api_id: 1234567
          api_hash: "your_api_hash_here"
          # phone_number: "+1234567890" # If needed for login
        ```

## Usage

Run the main script from the project's root directory:

```bash
python src/main.py
```

You can customize the path to the configuration file using the `--config` argument:

```bash
python src/main.py --config path/to/your/custom_config.yaml
```

## Project Structure (Simplified)

```
TelegramDownloader/
├── .gitignore
├── README.md
├── requirements.txt
├── src/
│   ├── main.py               # Main application entry point
│   ├── config.yaml           # Main configuration file (template/defaults)
│   ├── local_config.yaml     # Local configuration with secrets (gitignored)
│   ├── config_loader.py      # Loads and merges configurations
│   ├── client.py             # Telegram client setup
│   ├── downloader.py         # File downloading logic
│   ├── logger.py             # Logging setup and RobustLogger
│   ├── media_filter.py       # Media filtering logic
│   ├── message_parser.py     # Parses messages for media
│   ├── session_manager.py    # Manages Telegram sessions
│   └── tracker.py            # Tracks downloaded files
└── data/                     # Default directory for downloads, logs, sessions
    ├── downloads/
    ├── logs/
    └── sessions/
```
