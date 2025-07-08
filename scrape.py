"""
Scrape text from a given URL using Playwright and Trafilatura.

"""
# pylint: disable=broad-except

import random
import time
import re
import os
from pathlib import Path

from bs4 import BeautifulSoup

from trafilatura import extract

from dotenv import load_dotenv
load_dotenv()

FIREFOX_PROFILE_PATH = os.getenv("FIREFOX_PROFILE_PATH")


async def get_browser(playwright):
    """
    Initializes a Playwright browser instance with stealth settings.

    Args:
        playwright: The Playwright instance.

    Returns:
        Browser: The initialized browser instance.
    """
    viewport = random.choice([
        {"width": 1920, "height": 1080},
        {"width": 1366, "height": 768},
        {"width": 1440, "height": 900},
        {"width": 1536, "height": 864},
        {"width": 1280, "height": 720}
    ])

    # random device-scale-factor for additional randomization
    device_scale_factor = random.choice([1, 1.25, 1.5, 1.75, 2])

    # Random color scheme and timezone
    color_scheme = random.choice(['light', 'dark', 'no-preference'])
    timezone_id = random.choice([
        'America/New_York', 'Europe/London', 'Europe/Paris',
        'Asia/Tokyo', 'Australia/Sydney', 'America/Los_Angeles'
    ])
    locale = random.choice([
        'en-US', 'en-GB'
    ])
    extra_http_headers = {
        "Accept-Language": f"{locale.split('-')[0]},{locale};q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "DNT": "1" if random.choice([True, False]) else "0"
    }

    return await playwright.firefox.launch_persistent_context(
        user_data_dir=FIREFOX_PROFILE_PATH,
        headless=False,  # run headless, hide splash window
        viewport=viewport,
        device_scale_factor=device_scale_factor,
        timezone_id=timezone_id,
        color_scheme=color_scheme,
        extra_http_headers=extra_http_headers,
        # removes Playwright's default flag
        ignore_default_args=["--enable-automation"],
        args=[
            "--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"
        ],
        # provide a valid realistic User-Agent string for the latest Firefox on Apple Silicon
        user_agent="Mozilla/5.0 (Macintosh; ARM Mac OS X 14.4; rv:125.0) Gecko/20100101 Firefox/125.0",
        accept_downloads=True,
    )


def perform_human_like_actions(page):
    """Perform random human-like actions on a page to mimic real user behavior."""
    # Random mouse movements
    for _ in range(random.randint(3, 8)):
        # Move mouse with multiple steps to simulate human-like movement
        x = random.randint(100, 1200)
        y = random.randint(100, 700)
        steps = random.randint(5, 10)

        # Calculate increments for smooth movement
        for step in range(1, steps + 1):
            next_x = x * step / steps
            next_y = y * step / steps

            # Add slight randomness to path
            jitter_x = random.uniform(-5, 5)
            jitter_y = random.uniform(-5, 5)

            page.mouse.move(next_x + jitter_x, next_y + jitter_y)
            time.sleep(random.uniform(0.01, 0.05))

    # Random scrolling behavior
    scroll_amount = random.randint(300, 700)
    page.evaluate(f"window.scrollBy(0, {scroll_amount})")
    time.sleep(random.uniform(0.5, 2))

    # Sometimes scroll back up a bit
    if random.random() > 0.7:
        page.evaluate(f"window.scrollBy(0, -{random.randint(100, 300)})")
        time.sleep(random.uniform(0.3, 1))

    return page


def normalize_html(path: Path | str) -> str:
    """
    Clean and extract text content from an HTML file, including titles and social media metadata.

    Args:
        path (Path | str): Path to the HTML file to process

    Returns:
        - str: Extracted and cleaned text content, or empty string if processing fails

    The function extracts:
        - Page title from <title> tag
        - Social media titles from OpenGraph and Twitter meta tags
        - Social media descriptions from OpenGraph and Twitter meta tags
        - Main content using trafilatura library

    All extracted content is concatenated and truncated to MAX_INPUT_TOKENS length.
    """

    try:
        with open(path, 'r', encoding='utf-8') as file:
            html_content = file.read()
    except Exception as exc:
        print(f"Error: {str(exc)}")
        print(f"Skipping {path}")
        return ""

    # Parse the HTML content using trafilatura
    soup = BeautifulSoup(html_content, 'html.parser')

    try:
        # Try to get the title from the <title> tag
        title_tag = soup.find("title")
        title_str = "Page title: " + title_tag.string.strip() + \
            "\n" if title_tag and title_tag.string else ""
    except Exception as exc:
        title_str = ""
        print(str(exc), "clean_html page_title")

    try:
        # Try to get the title from the Open Graph meta tag
        og_title_tag = soup.find("meta", property="og:title")
        if not og_title_tag:
            og_title_tag = soup.find(
                "meta", attrs={"name": "twitter:title"})
        og_title = og_title_tag["content"].strip(
        ) + "\n" if og_title_tag and og_title_tag.get("content") else ""
        og_title = "Social card title: " + og_title if og_title else ""
    except Exception as exc:
        og_title = ""
        print(str(exc), "clean_html og_title")

    try:
        # get summary from social media cards
        og_desc_tag = soup.find("meta", property="og:description")
        if not og_desc_tag:
            # Extract the Twitter description
            og_desc_tag = soup.find(
                "meta", attrs={"name": "twitter:description"})
        og_desc = og_desc_tag.get("content").strip() + \
            "\n" if og_desc_tag else ""
        og_desc = 'Social card description: ' + og_desc if og_desc else ""
    except Exception as exc:
        og_desc = ""
        print(str(exc), "clean_html og_desc")

    # Get text and strip leading/trailing whitespace
    print(title_str + og_title + og_desc, "clean_html")
    try:
        plaintext = extract(html_content)
        plaintext = plaintext.strip() if plaintext else ""
    except Exception as exc:
        plaintext = html_content
        print(str(exc), "clean_html trafilatura")

    # remove special tokens, have found in artiles about tokenization
    # All OpenAI special tokens follow the pattern <|something|>
    special_token_re = re.compile(r"<\|\w+\|>")
    plaintext = special_token_re.sub("", plaintext)
    visible_text = title_str + og_title + og_desc + plaintext
    return visible_text
