from config import VECTOR_STORE_ID
import logging
from pathlib import Path

from scraper import load_articles, load_state
from upload_to_vectorstore import (
    upload_files,
    create_vector_store,
    attach_files_to_vector_store,
    attach_vector_store_to_assistant,
    get_client,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VS_NAME = "OptiSigns Docs"


def get_or_create_vector_store() -> str:
    if VECTOR_STORE_ID:
        logger.info(f"Reusing Vector Store: {VECTOR_STORE_ID}")
        return VECTOR_STORE_ID

    try:
        client = get_client()
        page = client.vector_stores.list(order="desc", limit=100)
        while True:
            for vs in page.data:
                if vs.name == VS_NAME and vs.status != "expired":
                    logger.info(
                        f"♻️  Found existing VS by name: {vs.id}  (status={vs.status})"
                    )
                    return vs.id
            if not page.has_next_page():
                break
            page = page.get_next_page()
    except Exception as exc:
        logger.warning(f"Could not list Vector Stores: {exc} — will create new one")
    return create_vector_store(VS_NAME)


def clean_stale_vs_files(vs_id: str):
    try:
        client = get_client()
        metadata = load_state()
        valid_article_ids = set(metadata.keys())

        existing = client.vector_stores.files.list(vector_store_id=vs_id)

        for vsf in existing.data:
            try:
                file_info = client.files.retrieve(vsf.id)

                slug = Path(file_info.filename).stem
                article_id = slug.split("-")[0]

                if article_id not in valid_article_ids:
                    client.vector_stores.files.delete(
                        vector_store_id=vs_id,
                        file_id=vsf.id,
                    )
                    client.files.delete(vsf.id)
            except Exception as e:
                logger.warning(f"Skip file {vsf.id}: {e}")
    except Exception as exc:
        logger.warning(f"Could not clean stale VS files: {exc}")


def main():
    # Step 1: load articles
    uploadPaths, summary = load_articles()
    # Step 2: upload files
    if not uploadPaths:
        logger.warning("No changes detected.")
        log_summary(summary)
        return

    file_ids = upload_files(uploadPaths)

    # Step 3: attach to vector store
    vector_store_id = get_or_create_vector_store()

    clean_stale_vs_files(vector_store_id)

    attach_files_to_vector_store(vector_store_id, file_ids)

    # Step 4: attach vector store to assistant
    attach_vector_store_to_assistant(vector_store_id)

    log_summary(summary)


def log_summary(summary):
    logger.info("\n--------------------------- Summary ---------------------------")
    logger.info(f"New: {summary['new']}")
    logger.info(f"Updated: {summary['updated']}")
    logger.info(f"Skipped: {summary['skipped']}")
    logger.info("--------------------------- Summary ---------------------------\n")


if __name__ == "__main__":
    main()
