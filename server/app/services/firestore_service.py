import firebase_admin
from firebase_admin import credentials, firestore
from app.config import Config
import os

class FirestoreService:
    _instance = None
    _db = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FirestoreService, cls).__new__(cls)
            cls._instance._initialize_firebase()
        return cls._instance

    def _initialize_firebase(self):
        if not firebase_admin._apps:
            # Ensure the path is correct and accessible
            if not os.path.exists(Config.FIREBASE_SERVICE_ACCOUNT_PATH):
                raise FileNotFoundError(
                    f"Firebase service account file not found at: {Config.FIREBASE_SERVICE_ACCOUNT_PATH}"
                )
            try:
                cred = credentials.Certificate(Config.FIREBASE_SERVICE_ACCOUNT_PATH)
                firebase_admin.initialize_app(cred)
                print("Firebase app initialized successfully.")
            except Exception as e:
                print(f"Error initializing Firebase app: {e}")
                raise
        self._db = firestore.client()

    def get_db(self):
        """Returns the Firestore client instance."""
        if self._db is None:
            # This case should ideally not happen if __new__ works correctly,
            # but good for robustness.
            self._initialize_firebase()
        return self._db

    # Example of a potential method to retrieve data (you'll customize this)
    def get_collection_data(self, collection_name: str):
        """Retrieves all documents from a specified Firestore collection."""
        try:
            docs = self.get_db().collection(collection_name).stream()
            data = [doc.to_dict() for doc in docs]
            return data
        except Exception as e:
            print(f"Error retrieving data from collection {collection_name}: {e}")
            return []

# Example usage (for testing purposes, remove in production main logic)
if __name__ == "__main__":
    # Ensure .env is loaded if running this file directly for testing
    from dotenv import load_dotenv
    load_dotenv()

    # You might need a dummy creds file for local testing if you don't want to use the real one
    # or ensure the real one is correctly placed for the test.
    # For a real run, ensure your service account JSON is in the 'credentials' folder.

    try:
        firestore_service = FirestoreService()
        db = firestore_service.get_db()
        print(f"Firestore client obtained: {db}")

        # Example: Try to fetch data from a test collection (replace 'your_test_collection' with a real one)
        # test_data = firestore_service.get_collection_data('your_test_collection')
        # print(f"Test data from 'your_test_collection': {test_data}")

    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        print("Please ensure your Firebase service account JSON is correctly placed in the 'credentials' folder and the path in config.py is correct.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")