from pathlib import Path
from config import OPENAI_API_KEY, ASSISTANT_ID

from openai import OpenAI
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_client():
    return OpenAI(api_key=OPENAI_API_KEY)


def upload_files(file_paths: list[Path]) -> list[str]:
    client = get_client()
    file_ids = []
    for idx, path in enumerate(file_paths, 1):
        try:
            with open(path, "rb") as f:
                file = client.files.create(file=f, purpose="assistants")
                file_ids.append(file.id)
        except Exception as e:
            logger.error(f"Failed to upload {path.name}: {e}")
    return file_ids


def create_vector_store(name: str) -> str:
    client = get_client()

    vector_store = client.vector_stores.create(
        name=name,
        chunking_strategy={
            "type": "static",
            "static": {
                "max_chunk_size_tokens": 500,
                "chunk_overlap_tokens": 100,
            },
        },
    )
    logger.info(f"📦 Vector Store created: {vector_store.id}  (name='{name}')")
    return vector_store.id


def attach_files_to_vector_store(vector_store_id: str, file_ids: list[str]):
    client = get_client()
    BATCH_SIZE = 32
    total_completed = 0
    total_failed = 0

    for i in range(0, len(file_ids), BATCH_SIZE):
        batch = file_ids[i : i + BATCH_SIZE]

        file_batch_obj = client.vector_stores.file_batches.create_and_poll(
            vector_store_id=vector_store_id,
            file_ids=batch,
        )

        completed = file_batch_obj.file_counts.completed
        failed = file_batch_obj.file_counts.failed
        total_completed += completed
        total_failed += failed
        logger.info(
            f"Batch {i // BATCH_SIZE + 1}: completed={completed}, failed={failed}"
        )

    logger.info(f"Total completed: {total_completed}, failed: {total_failed}")

    return total_completed, total_failed


def attach_vector_store_to_assistant(vector_store_id: str):
    if not ASSISTANT_ID:
        logger.warning("ASSISTANT_ID not found in environment variables")
        return

    client = get_client()

    assistant = client.beta.assistants.retrieve(ASSISTANT_ID)

    existing_vs = (
        assistant.tool_resources
        and assistant.tool_resources.file_search
        and assistant.tool_resources.file_search.vector_store_ids
    ) or []

    if vector_store_id in existing_vs:
        return

    client.beta.assistants.update(
        assistant_id=ASSISTANT_ID,
        tools=[{"type": "file_search"}],
        tool_resources={"file_search": {"vector_store_ids": [vector_store_id]}},
    )
