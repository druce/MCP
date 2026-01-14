#!/opt/anaconda3/envs/mcpskills/bin/python3
"""
SEC Filings Research Phase

Fetches and parses SEC 10-K filings, specifically Item 1 (Business Description).

Usage:
    ./skills/research_sec.py SYMBOL [--work-dir DIR]

    If --work-dir is not specified, creates work/SYMBOL_YYYYMMDD automatically.

Examples:
    ./skills/research_sec.py TSLA
    ./skills/research_sec.py AAPL --work-dir custom/directory

Output:
    - Creates 05_sec/ directory in work directory
    - 10k_item1.txt - Business description from latest 10-K
    - 10k_metadata.json - Filing metadata
"""

import os
import sys
import argparse
import json
import re
from datetime import datetime
from pathlib import Path

# Load environment
from dotenv import load_dotenv
load_dotenv()

# SEC EDGAR downloader
from sec_edgar_downloader import Downloader

# For parsing HTML
from bs4 import BeautifulSoup


def fetch_10k_item1(symbol, work_dir):
    """
    Fetch Item 1 (Business) from the latest 10-K filing.

    Args:
        symbol: Stock ticker symbol
        work_dir: Work directory path

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"Downloading 10-K filing for {symbol}...")

        # Get SEC credentials from environment
        sec_firm = os.getenv('SEC_FIRM')
        sec_user = os.getenv('SEC_USER')

        if not sec_firm or not sec_user:
            print(f"❌ ERROR: SEC_FIRM and SEC_USER must be set in .env file")
            print(f"   SEC requires User-Agent with company name and email")
            return False

        output_dir = os.path.join(work_dir, '05_sec')
        os.makedirs(output_dir, exist_ok=True)

        # Create temporary download directory
        temp_dir = os.path.join(output_dir, 'temp_download')
        os.makedirs(temp_dir, exist_ok=True)

        # Initialize downloader with company name and email from environment
        # SEC requires User-Agent with contact info
        dl = Downloader(sec_firm, sec_user, temp_dir)

        # Download the latest 10-K
        print(f"  Fetching latest 10-K from SEC EDGAR...")
        dl.get("10-K", symbol, limit=1)

        # Find the downloaded file
        print(f"  Parsing 10-K filing...")
        filing_path = None
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith('.txt'):
                    filing_path = os.path.join(root, file)
                    break
            if filing_path:
                break

        if not filing_path:
            print(f"❌ Could not find downloaded 10-K filing")
            return False

        # Read the filing
        with open(filing_path, 'r', encoding='utf-8', errors='ignore') as f:
            filing_text = f.read()

        # Extract Item 1
        item1_text = extract_item1(filing_text)

        if not item1_text:
            print(f"⚠ Could not automatically extract Item 1, saving full filing")
            item1_text = filing_text[:50000]  # First 50K characters

        # Save Item 1
        item1_path = os.path.join(output_dir, '10k_item1.txt')
        with open(item1_path, 'w', encoding='utf-8') as f:
            f.write(f"SEC 10-K Filing - Item 1 (Business)\n")
            f.write(f"Symbol: {symbol}\n")
            f.write(f"Downloaded: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"=" * 60 + "\n\n")
            f.write(item1_text)

        print(f"✓ Saved Item 1 to: {item1_path}")
        print(f"  Length: {len(item1_text):,} characters")

        # Save metadata
        metadata = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'filing_type': '10-K',
            'filing_path': filing_path,
            'item1_length': len(item1_text),
        }

        metadata_path = os.path.join(output_dir, '10k_metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"✓ Saved metadata to: {metadata_path}")

        # Clean up temp directory
        import shutil
        shutil.rmtree(temp_dir)

        return True

    except Exception as e:
        print(f"❌ Error downloading 10-K: {e}")
        import traceback
        traceback.print_exc()
        return False


def extract_item1(filing_text):
    """
    Extract Item 1 (Business) section from 10-K filing text.

    Args:
        filing_text: Full text of the 10-K filing

    Returns:
        str: Item 1 text or None if not found
    """
    try:
        # First, parse HTML and extract clean text
        soup = BeautifulSoup(filing_text, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()

        # Get text
        clean_text = soup.get_text()

        # Clean up whitespace
        lines = (line.strip() for line in clean_text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = '\n'.join(chunk for chunk in chunks if chunk)

        # Common patterns for Item 1 headers
        patterns = [
            r'(?i)ITEM\s+1[\.\:\s]+BUSINESS',
            r'(?i)ITEM\s+1[\.\:\-\—]+BUSINESS',
            r'(?i)Item 1\.\s+Business',
            r'(?i)Item 1\s+Business',
            r'(?i)ITEM\s+1\.',
            r'(?i)Item 1\s*\n',
        ]

        # Try to find Item 1 start
        start_pos = None
        for pattern in patterns:
            match = re.search(pattern, clean_text)
            if match:
                start_pos = match.start()
                print(f"  Found Item 1 at position {start_pos}")
                break

        if not start_pos:
            print(f"  Warning: Could not find Item 1 header")
            return None

        # Find Item 1A or Item 2 to determine end
        item2_patterns = [
            r'(?i)ITEM\s+1A[\.\:\s]+RISK\s+FACTORS',
            r'(?i)ITEM\s+1A[\.\:\-\—]+RISK',
            r'(?i)Item 1A\.\s+Risk',
            r'(?i)Item 1A\s+Risk',
            r'(?i)ITEM\s+1A\.',
            r'(?i)ITEM\s+2[\.\:\s]',
            r'(?i)Item 2\.',
        ]

        end_pos = None
        for pattern in item2_patterns:
            match = re.search(pattern, clean_text[start_pos+100:])  # Skip first 100 chars to avoid false matches
            if match:
                end_pos = start_pos + 100 + match.start()
                print(f"  Found end marker at position {end_pos}")
                break

        # If we can't find the end, take a reasonable chunk
        if not end_pos:
            end_pos = min(start_pos + 100000, len(clean_text))  # ~100K characters or end of text
            print(f"  No end marker found, using {end_pos - start_pos:,} characters")

        item1_text = clean_text[start_pos:end_pos]

        # Additional cleanup
        # Remove excessive whitespace
        item1_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', item1_text)

        # Remove page numbers and other artifacts
        item1_text = re.sub(r'^\d+\s*$', '', item1_text, flags=re.MULTILINE)

        # Remove table of contents entries (lines with dots and page numbers)
        item1_text = re.sub(r'^.*\.{3,}\s*\d+\s*$', '', item1_text, flags=re.MULTILINE)

        # Final whitespace cleanup
        item1_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', item1_text)

        print(f"  Extracted {len(item1_text):,} characters")
        return item1_text.strip()

    except Exception as e:
        print(f"  Warning: Error extracting Item 1: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='SEC filings research phase'
    )
    parser.add_argument(
        'symbol',
        help='Stock ticker symbol (e.g., TSLA, AAPL, MSFT)'
    )
    parser.add_argument(
        '--work-dir',
        default=None,
        help='Work directory path (default: work/SYMBOL_YYYYMMDD)'
    )

    args = parser.parse_args()

    # Normalize symbol
    symbol = args.symbol.upper()

    # Generate work directory if not specified
    if not args.work_dir:
        date_str = datetime.now().strftime('%Y%m%d')
        work_dir = os.path.join('work', f'{symbol}_{date_str}')
    else:
        work_dir = args.work_dir

    # Create work directory if it doesn't exist
    os.makedirs(work_dir, exist_ok=True)

    print("=" * 60)
    print("SEC Filings Research Phase")
    print("=" * 60)
    print(f"Symbol: {symbol}")
    print(f"Work Directory: {work_dir}")
    print("=" * 60)

    success_count = 0
    total_count = 1

    # Task 1: Fetch 10-K Item 1
    if fetch_10k_item1(symbol, work_dir):
        success_count += 1

    # Summary
    print("\n" + "=" * 60)
    print("SEC Research Phase Complete")
    print("=" * 60)
    print(f"Tasks completed: {success_count}/{total_count}")

    if success_count == total_count:
        print("✓ All tasks completed successfully")
        return 0
    elif success_count > 0:
        print(f"⚠ Partial success: {success_count}/{total_count} tasks completed")
        return 0
    else:
        print("❌ All tasks failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
