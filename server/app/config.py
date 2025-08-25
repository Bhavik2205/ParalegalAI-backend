# app/config.py (UPDATED with UPLOAD_FOLDER and ALLOWED_EXTENSIONS)

import os
from dotenv import load_dotenv
import logging # Import logging for the static method

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration."""
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # Firebase Service Account Path
    FIREBASE_SERVICE_ACCOUNT_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'credentials',
        'legal-dataset-firebase-adminsdk-fbsvc-8706c1b24f.json'
    )

    # --- NEW CONFIGURATION FOR FILE UPLOADS ---
    UPLOAD_FOLDER = 'uploads' # Path to store uploaded files relative to the server's root
    ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.docx', '.md'} # Allowed file extensions
    KEEP_UPLOADS = True # Set to True to keep uploaded files after processing, False to delete

    # Add other configurations as needed, e.g., logging levels, database connections

    @staticmethod
    def load_openai_api_key():
        """Helper to explicitly check and log API key status."""
        if not Config.OPENAI_API_KEY:
            logging.error("OPENAI_API_KEY environment variable not set in .env file.")
            # Consider raising an error or exiting if the API key is critical for startup
            # import sys
            # sys.exit(1)
        else:
            logging.info("OPENAI_API_KEY loaded successfully.")