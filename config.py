from dotenv import load_dotenv
import os

load_dotenv()  # Load variables from .env

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = os.getenv("BASE_URL", "https://openrouter.ai/api/v1")
