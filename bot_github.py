import os
import json
import logging
import re
import time
from urllib.parse import urljoin

import requests
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright


# ============================================================
# CONFIG
# ============================================================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

NEWS_URL = "https://www.forexfactory.com/news"

PROCESSED_FILE = "processed_news.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# ============================================================
# US NEWS FILTER
# ============================================================

US_TERMS = [

    # United States
    "u.s.",
    "u.s",
    "us economy",
    "us dollar",
    "u.s. dollar",
    "united states",
    "american economy",
    "american workers",

    # Federal Reserve
    "federal reserve",
    "fed ",
    "fed's",
    "powell",
    "fomc",

    # US government
    "donald trump",
    "trump",
    "white house",
    "u.s. treasury",
    "us treasury",
    "treasury secretary",

    # Employment
    "u.s. jobs",
    "us jobs",
    "u.s. employment",
    "us employment",
    "u.s. labor",
    "us labor",
    "nonfarm payroll",
    "non-farm payroll",
    "payrolls",

    # Inflation
    "u.s. inflation",
    "us inflation",
    "u.s. cpi",
    "us cpi",
    "consumer price index",
    "u.s. pce",
    "us pce",

    # Economy
    "u.s. gdp",
    "us gdp",
    "u.s. economy",
    "us economy",

    # Trade
    "u.s. tariffs",
    "us tariffs",
    "u.s. trade",
    "us trade",

    # Politics / institutions
    "congress",
    "senate",
    "supreme court",

]


FALSE_POSITIVES = [

    # Currency symbols/pairs
    "xauusd",
    "usdjpy",
    "usdchf",
    "usdcad",
    "audusd",
    "nzdusd",
    "eurusd",
    "gbpusd",

    # Unrelated subjects
    "fifa",
    "football",
    "soccer",
    "movie",
    "film",
    "superhero",
    "celebrity",

]


def is_us_related(title):

    text = title.lower()

    # Reject obvious unrelated subjects
    for word in FALSE_POSITIVES:

        if word in text:

            # Unless another strong US keyword exists
            if not any(term in text for term in US_TERMS):
                return False

    # Strong US keyword
    for term in US_TERMS:

        if term in text:
            return True

    return False


# ============================================================
# PROCESSED NEWS
# ============================================================

def load_processed():

    if not os.path.exists(PROCESSED_FILE):
        return set()

    try:

        with open(
            PROCESSED_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        return set(data)

    except Exception as e:

        logger.warning(
            "Could not load processed news: %s",
            e
        )

        return set()


def save_processed(processed):

    with open(
        PROCESSED_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            sorted(processed),
            f,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# TELEGRAM
# ============================================================

def send_telegram(title, url):

    message = (
        "🇺🇸 US NEWS\n\n"
        f"📰 {title}\n\n"
        f"🔗 {url}"
    )

    api_url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendMessage"
    )

    response = requests.post(
        api_url,
        data={
            "chat_id": CHAT_ID,
            "text": message,
            "disable_web_page_preview": False,
        },
        timeout=20
    )

    if response.status_code != 200:

        logger.error(
            "Telegram error: %s",
            response.text
        )

        return False

    logger.info(
        "Telegram message sent successfully."
    )

    return True


# ============================================================
# FETCH FOREX FACTORY
# ============================================================

def fetch_news():

    logger.info(
        "Opening Forex Factory..."
    )

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        page = browser.new_page(
            viewport={
                "width": 1366,
                "height": 768
            },

            user_agent=(
                "Mozilla/5.0 "
                "(X11; Linux x86_64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/131.0.0.0 "
                "Safari/537.36"
            ),

            locale="en-US"
        )

        try:

            page.goto(
                NEWS_URL,
                wait_until="domcontentloaded",
                timeout=60000
            )

            page.wait_for_timeout(8000)

            logger.info(
                "Page title: %s",
                page.title()
            )

            title = page.title().lower()

            if (
                "just a moment" in title
                or "security verification" in page.content().lower()
            ):

                logger.warning(
                    "Cloudflare verification detected."
                )

                return []

            stories = []

            links = page.locator("a").all()

            for link in links:

                try:

                    story_title = (
                        link.inner_text()
                        .strip()
                    )

                    href = link.get_attribute(
                        "href"
                    )

                    if not story_title or not href:
                        continue

                    if not re.match(
                        r"^/news/\d+-[^/#]+$",
                        href
                    ):
                        continue

                    url = urljoin(
                        NEWS_URL,
                        href
                    )

                    stories.append(
                        {
                            "title": " ".join(
                                story_title.split()
                            ),
                            "url": url,
                            "id": href.split("/")[2].split("-")[0]
                        }
                    )

                except Exception:
                    continue

            browser.close()

            # Remove duplicates
            unique = {}

            for story in stories:
                unique[story["id"]] = story

            stories = list(unique.values())

            logger.info(
                "Found %d news stories",
                len(stories)
            )

            return stories

        except Exception as e:

            logger.error(
                "Forex Factory error: %s",
                e
            )

            browser.close()

            return []


# ============================================================
# MAIN
# ============================================================

def main():

    logger.info(
        "Starting GitHub Forex Factory News Bot"
    )

    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN secret is missing."
        )

    if not CHAT_ID:
        raise RuntimeError(
            "CHAT_ID secret is missing."
        )

    processed = load_processed()

    stories = fetch_news()

    if not stories:

        logger.warning(
            "No news retrieved."
        )

        return

    new_count = 0

    for story in stories:

        story_id = story["id"]
        title = story["title"]
        url = story["url"]

        if story_id in processed:
            continue

        # Mark every successfully retrieved story
        # so old news is not sent later.
        if is_us_related(title):

            logger.info(
                "🇺🇸 US NEWS: %s",
                title
            )

            if send_telegram(
                title,
                url
            ):

                processed.add(
                    story_id
                )

                new_count += 1

        else:

            processed.add(
                story_id
            )

    save_processed(
        processed
    )

    logger.info(
        "New US news sent: %d",
        new_count
    )

    logger.info(
        "Processed news total: %d",
        len(processed)
    )


if __name__ == "__main__":
    main()
