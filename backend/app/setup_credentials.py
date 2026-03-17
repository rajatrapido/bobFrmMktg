import os
import json
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()

def setup_credentials():
    bucket_name = os.getenv("BUCKET_NAME")
    blob_name = os.getenv("BLOB_NAME")
    local_json_path = "/Users/E2005/projects/bobfrmmktg/backend/app/service_account.json"

    if not os.path.exists(local_json_path):
        print(f"Downloading credentials from GCS bucket: {bucket_name}, blob: {blob_name}...")
        try:
            # Clear env var temporarily so storage.Client doesn't look for the missing file
            creds_env = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
            if creds_env:
                del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
            
            storage_client = storage.Client()
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            json_key_string = blob.download_as_text()
            
            # Put it back if needed
            if creds_env:
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_env
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(local_json_path), exist_ok=True)
            
            with open(local_json_path, "w") as f:
                f.write(json_key_string)
            print("Credentials downloaded successfully.")
        except Exception as e:
            print(f"Failed to download credentials: {e}")
            # If we fail to download, we can't proceed
            exit(1)
    else:
        print("Credentials already exist locally.")

if __name__ == "__main__":
    setup_credentials()
