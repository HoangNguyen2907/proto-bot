import logging

from scraper import load_articles


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    new_articles, updated_articles, skipped_articles = load_articles()
    logger.info("New articles: %s", len(new_articles))
    logger.info("Updated articles: %s", len(updated_articles))
    logger.info("Skipped articles: %s", len(skipped_articles))


if __name__ == "__main__":
    main()
