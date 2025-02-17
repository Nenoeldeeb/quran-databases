# Quran Data Tools

## Description

This project provides tools for downloading and processing Quran data. It includes scripts to:

- Download Quran pages in JSON format from online sources (`get_quran_pages.py`).
- Extract chapter names from a Quran data file (`get_chapters_names.py`).
- Build a SQLite database from downloaded Quran data and chapter names (`build_quran_db.py`).

The `quran_data` directory downloaded JSON files of Quran pages in different editions (e.g., `ara-quransimple`, `ara-quranuthmanienc`, `ara-quranuthmanihaf`, `ara-quranuthmanihaf1`).

The `databases` directory contains created SQLite files from downloaded Quran pages in different editions (e.g., `ara-quransimple`, `ara-quranuthmanienc`, `ara-quranuthmanihaf`, `ara-quranuthmanihaf1`).

`quran_chapters_names.json` contains chapter names in JSON format.

`quran_info.json` contains information about the Holy Quran (e.g.. chapters and its info, verses and its text & count, pages and maqraas etc)

`uthmanic-hafs-ver13.ttf` Use It to display both "ara-quranuthmanienc" & "ara-quranuthmanihaf" correctly.

## Installation

To install and run this project, follow these steps:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Nenoeldeeb/quran-databases.git
   cd quran-databases
   ```

2. **Set up a virtual environment (recommended):**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   This project requires the `aiohttp` library for asynchronous HTTP requests. And `requests` for normal HTTP requests. Ensure you have them installed. The dependencies are listed in the `requirements.txt` file.

## Usage

### 1. Download Quran Pages:
   Run `get_quran_pages.py` to download Quran pages in JSON format.

   **Command-line arguments:**
   - `-e` or `--edition`: Specify the Quran edition to download. Available editions are listed in `config.py` under `QURAN_EDITIONS`. If not provided, a selection menu will appear.
   - `-b` or `--batch-size`: Set the batch size for downloading pages concurrently (default: 50).
   - `-m` or `--max-concurrent`: Set the maximum number of concurrent connections (default: 8).

   **Example:**
   ```bash
   python get_quran_pages.py -e ara-quransimple -b 20 -m 10
   ```
   This command downloads the `ara-quransimple` edition, using a batch size of 20 and a maximum of 10 concurrent connections.

### 2. Get Chapter Names:
   Run `get_chapters_names.py` to extract chapter names from a Quran info JSON file (downloaded from API) and save them to `quran_chapters_names.json`.

   **No command-line arguments.** The script uses `quran_info.json` as input and saves the output to `quran_data/quran_chapters_names.json`.

   **Example:**
   ```bash
   python get_chapters_names.py
   ```

### 3. Build Quran Database:
   Run `build_quran_db.py` to create a SQLite database from the downloaded Quran data and chapter names.

   **Command-line arguments:**
   - `-e` or `--edition`: Specify the Quran edition for which to build the database. Available editions are listed in `config.py` under `QURAN_EDITIONS`. If not provided, a selection menu will appear.

   **Example:**
   ```bash
   python build_quran_db.py -e ara-quransimple
   ```

## Modification

To add more Quran editions You can :
 - Modify `config.py` file just add the edition name in "QURAN_EDITIONS" list.
 - Then run `get_quran_pages.py` to download the edition JSON files. Also, Run `build_quran_db.py` if You want to get a database of this edition.


If You want to get all available editions:
 - Just copy the "BASE_URL" from `config.py` then append "editions.json" at the end. Then paste It in the browser and press enter.

## License

AGPL-3.0 License

This project is open-source and available under the AGPL-3.0 License. See the `LICENSE` file for more details.

## Credets
This project totally build with a help of API from brother's repo [Fawaz Ahmed](https://github.com/fawazahmed0/quran-api.git)
