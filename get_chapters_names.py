import json
import logging
from pathlib import Path
from typing import Dict, Optional
import requests
from os.path import join

from config import QURAN_INFO, INDENT_SIZE, DATA_DIR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_quran_chapters_names(input_file_path: str, output_file_path: str) -> None:
    """
    Extracts chapter numbers and Arabic names from a Quran JSON file and saves them to a new JSON file.

    Args:
        input_file_path: The path to the input JSON file.
        output_file_path: The path to the output JSON file.
    """
    input_path = Path(input_file_path)
    output_path = Path(output_file_path)
    
    # Ensure parent directories exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Get or download the input file
    quran_data = _get_quran_data(input_path)
    if not quran_data:
        logger.error(f"Failed to get Quran data from {input_path}")
        return

    try:
        # Extract chapter names
        chapters = quran_data.get("chapters", [])
        chapter_names: Dict[int, str] = {
            chapter["chapter"]: chapter["arabicname"] for chapter in chapters
        }
        
        # Save to output file
        with open(output_path, "w", encoding="utf-8") as o:
            json.dump(chapter_names, o, ensure_ascii=False, indent=INDENT_SIZE)
        
        logger.info(f"Successfully extracted {len(chapter_names)} chapter names to {output_path}")
        
    except KeyError as e:
        logger.error(f"Missing expected key in JSON data: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")


def _get_quran_data(input_path: Path) -> Optional[Dict]:
    """Gets Quran data from file or downloads it if file doesn't exist"""
    if input_path.exists():
        try:
            with open(input_path, encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON format in {input_path}")
            return None
    else:
        logger.info(f"Input file not found at {input_path}, downloading from API")
        try:
            res = requests.get(QURAN_INFO, timeout=30)
            res.raise_for_status()
            
            # Ensure parent directory exists
            input_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(input_path, "w", encoding="utf-8") as f:
                json.dump(res.json(), f, ensure_ascii=False, indent=INDENT_SIZE)
            
            return res.json()
        except requests.RequestException as e:
            logger.error(f"Failed to download Quran info: {e}")
            return None


if __name__ == "__main__":
    input_file = join(DATA_DIR, "quran_info.json")
    output_file = join(DATA_DIR, "quran_chapters_names.json")
    get_quran_chapters_names(input_file, output_file)