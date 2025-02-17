import argparse
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import json
from os.path import join
from pathlib import Path
import time
from typing import Any, Dict, List, Optional

import aiohttp

from config import DATA_DIR, INDENT_SIZE, QURAN_EDITIONS, QURAN_PAGES, DEFAULT_BATCH_SIZE, DEFAULT_MAX_CONCURRENT


@dataclass
class DownloadResult:
    page_num: int
    data: Optional[Dict[str, Any]]


class QuranDownloader:
    def __init__(self, quran_edition: str, start_page: int = 1, end_page: int = 604, 
                 batch_size: int = DEFAULT_BATCH_SIZE, max_concurrent: int = DEFAULT_MAX_CONCURRENT):
        self.start_page = start_page
        self.end_page = end_page
        self.quran_edition = quran_edition
        self.edition_dir = Path(join(DATA_DIR, quran_edition))
        self.complete_file = self.edition_dir / f"{quran_edition}.json"
        self.batch_size = batch_size
        self.base_url = QURAN_PAGES.format(quran_edition, "{}")
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
    async def download_page(self, session: aiohttp.ClientSession, page_num: int) -> DownloadResult:
        """Download a single page asynchronously"""
        url = self.base_url.format(page_num)
        output_file = self.edition_dir / f"page_{page_num}.json"

        try:
            async with self.semaphore:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        page_object = {
                            f"page_{page_num}": data["pages"]
                        }
                        
                        await self._save_json_async(output_file, page_object)
                        return DownloadResult(page_num, page_object)
                    else:
                        print(f"Error downloading page {page_num}: Status {response.status}")
                        return DownloadResult(page_num, None)

        except Exception as e:
            print(f"Error processing page {page_num}: {str(e)}")
            return DownloadResult(page_num, None)

    async def _save_json_async(self, filename: Path, data: Dict) -> None:
        """Save JSON data to file asynchronously"""
        def _write_json():
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=INDENT_SIZE)
                
        with ThreadPoolExecutor() as pool:
            await asyncio.get_event_loop().run_in_executor(pool, _write_json)

    async def process_batch(self, session: aiohttp.ClientSession, batch_pages: range) -> List[Dict]:
        """Process a batch of pages concurrently"""
        tasks = [self.download_page(session, page_num) for page_num in batch_pages]
        results = await asyncio.gather(*tasks)
        return [result.data for result in results if result.data is not None]

    async def download_all(self) -> None:
        """Download all pages in batches"""
        # Create directory if it doesn't exist
        self.edition_dir.mkdir(exist_ok=True)

        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            all_pages = []
            
            # Process pages in batches
            for batch_start in range(self.start_page, self.end_page + 1, self.batch_size):
                batch_end = min(batch_start + self.batch_size, self.end_page + 1)
                batch_pages = range(batch_start, batch_end)
                
                print(f"Processing pages {batch_start} to {batch_end-1}...")
                batch_results = await self.process_batch(session, batch_pages)
                all_pages.extend(batch_results)
                
                # Show progress
                pages_processed = len(all_pages)
                elapsed_time = time.time() - start_time
                pages_per_second = pages_processed / elapsed_time if elapsed_time > 0 else 0
                print(f"Processed {pages_processed} pages. "
                      f"Speed: {pages_per_second:.2f} pages/second")

            # Create and save the final combined file
            complete_quran = {"pages": all_pages}
            await self._save_json_async(self.complete_file, complete_quran)

            total_time = time.time() - start_time
            print(f"\nDownload complete!")
            print(f"Total time: {total_time:.2f} seconds")
            print(f"Average speed: {len(all_pages)/total_time:.2f} pages/second")
            print(f"Individual pages saved in: {self.edition_dir}")
            print(f"Combined Quran saved as: {self.complete_file}")
            print(f"Total pages processed: {len(all_pages)}")


def get_user_selection() -> str:
    """Get and validate user selection of Quran edition"""
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


async def main() -> None:
    parser = argparse.ArgumentParser(description="Download Quran pages from API")
    parser.add_argument("-e", "--edition", type=str, help="Specify edition directly instead of selection menu")
    parser.add_argument("-b", "--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help="Batch size for downloads")
    parser.add_argument( "-m", "--max-concurrent", type=int, default=DEFAULT_MAX_CONCURRENT, help="Maximum concurrent connections")
    args = parser.parse_args()
    
    edition = args.edition if args.edition else get_user_selection()
    
    downloader = QuranDownloader(
        quran_edition=edition,
        batch_size=args.batch_size,
        max_concurrent=args.max_concurrent
    )
    
    await downloader.download_all()


if __name__ == "__main__":
    # Install required packages:
    # pip install aiohttp
    asyncio.run(main())