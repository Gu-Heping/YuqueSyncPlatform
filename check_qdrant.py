import os
# Set NO_PROXY before importing/using clients that might use it
os.environ["NO_PROXY"] = "localhost,127.0.0.1"

from qdrant_client import QdrantClient
from qdrant_client.http.models import CollectionDescription
import sys

def check_connection():
    url = "http://localhost:6333"
    print(f"Attempting to connect to Qdrant at {url}...")
    
    try:
        client = QdrantClient(url=url)
        # Try to get collections to verify connection
        collections = client.get_collections()
        print(f"✅ Connection successful!")
        print(f"Collections found: {collections}")
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    success = check_connection()
    if not success:
        sys.exit(1)
