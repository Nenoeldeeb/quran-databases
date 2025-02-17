import json
import logging
from pathlib import Path
import sqlite3
import argparse
from typing import Dict, List, Optional
from contextlib import contextmanager
from os.path import join

from config import QURAN_EDITIONS, DB_DIR, DATA_DIR, DB_PRAGMAS

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class QuranDatabaseBuilder:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        
    @contextmanager
    def get_connection(self):
        """Context manager for database connection"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Apply performance pragmas
            for pragma in DB_PRAGMAS:
                cursor.execute(pragma)
                
            yield conn, cursor
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
                
    def create_tables(self):
        """Create all required database tables and indexes"""
        with self.get_connection() as (conn, cursor):
            # Chapters table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chapters (
                    chapter_id INTEGER PRIMARY KEY,
                    chapter_name TEXT NOT NULL,
                    total_verses INTEGER NOT NULL,
                    CONSTRAINT valid_total_verses CHECK (total_verses > 0)
                )
            ''')

            # Verses table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS verses (
                    verse_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chapter_id INTEGER NOT NULL,
                    verse_number INTEGER NOT NULL,
                    verse_text TEXT NOT NULL,
                    FOREIGN KEY (chapter_id) REFERENCES chapters(chapter_id),
                    UNIQUE(chapter_id, verse_number),
                    CONSTRAINT valid_verse_number CHECK (verse_number > 0)
                )
            ''')

            # Pages table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pages (
                    page_id INTEGER PRIMARY KEY
                )
            ''')

            # Page_verses table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS page_verses (
                    page_id INTEGER NOT NULL,
                    verse_id INTEGER NOT NULL,
                    verse_order INTEGER NOT NULL,
                    starts_new_chapter BOOLEAN NOT NULL DEFAULT 0,
                    FOREIGN KEY (page_id) REFERENCES pages(page_id),
                    FOREIGN KEY (verse_id) REFERENCES verses(verse_id),
                    PRIMARY KEY (page_id, verse_id),
                    UNIQUE (page_id, verse_order)
                )
            ''')

            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_verses_chapter ON verses(chapter_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_page_verses_order ON page_verses(page_id, verse_order)')
            
            conn.commit()
            logger.info("Database tables and indexes created successfully")

    def load_data(self, quran_path: Path, chapters_names_path: Path):
        """Load data from JSON files into the database"""
        try:
            # Load JSON files
            quran_data = self._load_json(quran_path)
            chapters_names = self._load_json(chapters_names_path)
            
            if not quran_data or not chapters_names:
                logger.error("Failed to load required JSON data")
                return

            with self.get_connection() as (conn, cursor):
                # First pass: Calculate verse counts per chapter
                chapter_verse_counts = self._calculate_verse_counts(quran_data['pages'])

                # Insert chapters
                self._insert_chapters(cursor, chapters_names, chapter_verse_counts)

                # Insert pages and verses
                self._insert_pages_and_verses(cursor, quran_data['pages'])
                
                conn.commit()
                logger.info("Data loaded successfully")
                
                # Verify data integrity
                self._verify_data_integrity(cursor)
                
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            raise

    def _load_json(self, path: Path) -> Optional[Dict]:
        """Load and parse JSON file"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Error loading JSON from {path}: {e}")
            return None

    def _calculate_verse_counts(self, pages_data: List[Dict]) -> Dict[int, int]:
        """Calculate total verses per chapter"""
        chapter_verse_counts = {}
        for page_data in pages_data:
            for verses in page_data.values():
                for verse in verses:
                    chapter_id = verse['chapter']
                    chapter_verse_counts[chapter_id] = chapter_verse_counts.get(chapter_id, 0) + 1
        return chapter_verse_counts

    def _insert_chapters(self, cursor: sqlite3.Cursor, chapters_names: Dict, 
                          verse_counts: Dict[int, int]):
        """Insert chapters with verse counts"""
        for chapter_number_str, chapter_name in chapters_names.items():
            chapter_id = int(chapter_number_str)
            total_verses = verse_counts.get(chapter_id, 0)
            if total_verses == 0:
                logger.warning(f"No verses found for chapter {chapter_id}")
                continue
                
            cursor.execute('''
                INSERT INTO chapters (chapter_id, chapter_name, total_verses) 
                VALUES (?, ?, ?)
            ''', (chapter_id, chapter_name, total_verses))
            
    def _insert_pages_and_verses(self, cursor: sqlite3.Cursor, pages_data: List[Dict]):
        """Insert pages and verses with proper relationships"""
        verse_cache = {}  # Cache to avoid duplicate verse insertions
            
        for page_data in pages_data:
            for page_num_str, verses in page_data.items():
                page_num = int(page_num_str.split('_')[1])
                
                # Insert page
                try:
                    cursor.execute('INSERT INTO pages (page_id) VALUES (?)', (page_num,))
                except sqlite3.IntegrityError:
                    # Page might already exist, continue
                    pass
                
                # Process verses on this page
                current_chapter = None
                verse_order = 0
                
                for verse in verses:
                    chapter_id = verse['chapter']
                    verse_number = verse['verse']
                    
                    # Generate a unique key for verse caching
                    verse_key = f"{chapter_id}_{verse_number}"
                    
                    # Insert verse if not already in cache
                    if verse_key not in verse_cache:
                        cursor.execute('''
                            INSERT INTO verses (chapter_id, verse_number, verse_text)
                            VALUES (?, ?, ?)
                        ''', (chapter_id, verse_number, verse['text']))
                        verse_cache[verse_key] = cursor.lastrowid
                    
                    verse_id = verse_cache[verse_key]
                    starts_new_chapter = (current_chapter != chapter_id)
                    
                    # Link verse to page and track order
                    cursor.execute('''
                        INSERT INTO page_verses (page_id, verse_id, verse_order, starts_new_chapter)
                        VALUES (?, ?, ?, ?)
                    ''', (page_num, verse_id, verse_order, starts_new_chapter))
                    
                    current_chapter = chapter_id
                    verse_order += 1

    def _verify_data_integrity(self, cursor: sqlite3.Cursor):
        """Verify data integrity after loading"""
        try:
            # Verify chapter verse counts
            cursor.execute('''
                SELECT c.chapter_id, c.total_verses, COUNT(v.verse_id) as actual_verses
                FROM chapters c
                LEFT JOIN verses v ON c.chapter_id = v.chapter_id
                GROUP BY c.chapter_id
                HAVING c.total_verses != actual_verses
            ''')
            discrepancies = cursor.fetchall()
            if discrepancies:
                logger.warning(f"Found verse count discrepancies in chapters: {discrepancies}")

            # Verify page verse ordering
            cursor.execute('''
                SELECT page_id, COUNT(*) as duplicate_orders
                FROM page_verses
                GROUP BY page_id, verse_order
                HAVING duplicate_orders > 1
            ''')
            duplicate_orders = cursor.fetchall()
            if duplicate_orders:
                logger.warning(f"Found duplicate verse orders on pages: {duplicate_orders}")

        except sqlite3.Error as e:
            logger.error(f"Error verifying data integrity: {e}")
            raise


def get_user_edition_selection() -> str:
    """Get user selection for Quran edition"""
    choices = "\n".join(f"{i}: {edition}" for i, edition in enumerate(QURAN_EDITIONS, 1))

    while True:
        print("Select Quran edition:")
        print(choices)
        print("0: Exit")
        
        try:
            edition = input("Enter the number of the edition: ")
            if edition == "0":
                print("Goodbye!")
                exit(0)
                
            edition_num = int(edition)
            if 1 <= edition_num <= len(QURAN_EDITIONS):
                return QURAN_EDITIONS[edition_num - 1]
                
            print(f"Invalid choice. Please enter a number between 1 and {len(QURAN_EDITIONS)}")
        except ValueError:
            print("Please enter a valid number")


def main():
    parser = argparse.ArgumentParser(description="Build Quran SQLite database")
    parser.add_argument( "-e", "--edition", type=str, help="Specify edition directly instead of selection menu")
    args = parser.parse_args()
    
    edition = args.edition if args.edition else get_user_edition_selection()
    
    # Construct paths
    edition_dir = DATA_DIR / edition
    quran_json_path = edition_dir / f"{edition}.json"
    chapters_names_path = Path(join(DATA_DIR, "quran_chapters_names.json"))
    db_path = DB_DIR / f"{edition}.db"
    
    # Check if required files exist
    if not quran_json_path.exists():
        logger.error(f"Quran data file not found: {quran_json_path}")
        print(f"Please run get_quran_pages.py first to download the {edition} edition")
        return

    if not chapters_names_path.exists():
        logger.error(f"Chapter names file not found: {chapters_names_path}")
        print("Please run get_chapters_names.py first to extract chapter information")
        return

    try:
        db_builder = QuranDatabaseBuilder(db_path)
        db_builder.create_tables()
        db_builder.load_data(quran_json_path, chapters_names_path)
        logger.info(f"Database '{db_path}' created and populated successfully")
    except Exception as e:
        logger.error(f"Failed to set up database: {e}")


if __name__ == "__main__":
    main()