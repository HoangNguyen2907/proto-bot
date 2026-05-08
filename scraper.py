import os
import re
import json
from pathlib import Path

import requests
import logging

from markdownify import markdownify as md
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MARKDOWN_DIR = "data/markdown"
METADATA_FILE = "data/metadata.json"
BASE_URL = "https://support.optisigns.com/api/v2/help_center/en-us/articles.json"

os.makedirs(MARKDOWN_DIR, exist_ok=True)

if not os.path.exists(METADATA_FILE):
    with open(METADATA_FILE, "w") as f:
        json.dump({}, f)


def load_state():
    with open(METADATA_FILE, "r") as f:
        metadata = json.load(f)
    return metadata


def save_state(state):
    with open(METADATA_FILE, "w") as f:
        json.dump(state, f, indent=2)


def fetch_articles():
    articles = []
    url = BASE_URL
    while True:
        respone = requests.get(url)
        data = respone.json()
        articles.extend(data.get("articles", []))
        next_page = data.get("next_page")

        if len(articles) >= 60:
            break

        url = next_page
    return articles


def article_to_markdown(article):
    body = article.get("body", "")
    title = article.get("title", "")
    url = article.get("html_url", "")

    soup = BeautifulSoup(body, "html.parser")

    for element in soup.select(
        "nav, header, footer, aside, script, style, ins, svg, form, img, iframe, .ads, .advertisement, #sidebar"
    ):
        element.decompose()

    clean_html = str(soup.find("article") or soup.find("main") or soup)
    markdown = md(clean_html, heading_style="ATX")

    lines = [line.strip() for line in markdown.splitlines()]

    compact_lines = []

    previous_empty = False

    for line in lines:
        is_empty = line.strip() == ""

        if is_empty and previous_empty:
            continue

        compact_lines.append(line)

        previous_empty = is_empty

    markdown = "\n".join(compact_lines)

    return f"""
# {title}

Article URL: {url}

{markdown}
""".strip()


def save_markdown(article):
    title = article.get("title", "")
    article_id = article.get("id", "")
    clean_title = re.sub(r"[^a-z0-9\s]", " ", title.lower())
    slug = "-".join(clean_title.split())
    markdown = article_to_markdown(article)
    file_path = os.path.join(MARKDOWN_DIR, f"{article_id}-{slug}.md")

    with open(file_path, "w") as f:
        f.write(markdown)

    return file_path


def load_articles() -> tuple[list[Path], dict[str, int]]:
    articles = fetch_articles()
    state = load_state()
    uploadPaths: list[Path] = []
    summary = {
        "new": 0,
        "updated": 0,
        "skipped": 0,
    }

    for article in articles:
        article_id = str(article.get("id", ""))
        edited_at = article.get("edited_at", "")
        if article_id not in state:
            path = save_markdown(article)
            uploadPaths.append(path)
            state[article_id] = {
                "edited_at": edited_at,
            }
            summary["new"] += 1
        elif state[article_id]["edited_at"] != edited_at:
            path = save_markdown(article)
            uploadPaths.append(path)
            state[article_id] = {"edited_at": edited_at}
            summary["updated"] += 1
        else:
            summary["skipped"] += 1

    save_state(state)
    return uploadPaths, summary
