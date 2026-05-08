import os
from dotenv import load_dotenv

APP_ENV = os.getenv("APP_ENV", "local")

if APP_ENV == "local":
    load_dotenv(".env.local")


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
VECTOR_STORE_ID = os.getenv("VECTOR_STORE_ID")
