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
    body_html = article.get("body") or ""
    title = article.get("title", "Untitled Article")
    url = article.get("html_url", "")

    if not body_html:
        return ""

    soup = BeautifulSoup(body_html, "html.parser")

    # 1. Loại bỏ các thành phần gây nhiễu (Nav, Ads, Social Media, Scripts)
    trash_selectors = [
        "nav",
        "header",
        "footer",
        "aside",
        "script",
        "style",
        "ins",
        "svg",
        "form",
        ".ads",
        ".advertisement",
        ".article-sidebar",
        ".article-subscribe",
        ".article-votes",
        ".article-comments",
        ".article-rel-container",
        ".article-author",
    ]
    for selector in trash_selectors:
        for element in soup.select(selector):
            element.decompose()

    clean_markdown = md(
        str(soup),
        heading_style="ATX",
        bullets="*",
        strip=["img"],
    )

    clean_markdown = re.sub(r"\[([^\]]+)\]\(\#[^\)]+\)", r"\1", clean_markdown)

    clean_markdown = re.sub(r"\n{3,}", "\n\n", clean_markdown)

    url_tag = f"Article URL: {url}"

    def inject_url_after_heading(match):
        return f"{match.group(0)}\n{url_tag}\n"

    content_with_url = re.sub(
        r"^(#{1,3} .+)$",
        inject_url_after_heading,
        clean_markdown.strip(),
        flags=re.MULTILINE,
    )

    final_output = [
        f"# {title}",
        url_tag,
        "",
        content_with_url,
        "",
        url_tag,
    ]

    return "\n".join(final_output)


def save_markdown(article):
    article_id = article.get("id", "")
    markdown = article_to_markdown(article)
    file_path = os.path.join(MARKDOWN_DIR, f"{article_id}.md")
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
