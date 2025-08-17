import os
import requests
from dotenv import load_dotenv
from tqdm import tqdm
import time
import logging
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

# Bluesky API details
BSKY_USERNAME = os.getenv("BSKY_USERNAME")
BSKY_PASSWORD = os.getenv("BSKY_PASSWORD")
BSKY_PDS_URL = os.getenv("BSKY_PDS_URL", "https://bsky.social")

class BlueskySearchClient:
    def __init__(self, pds_url: str, username: str, password: str):
        self.pds_url = pds_url
        self.session_url = f"{self.pds_url}/xrpc/com.atproto.server.createSession"
        self.search_url = f"{self.pds_url}/xrpc/app.bsky.feed.searchPosts"
        self.username = username
        self.password = password
        self.jwt = None
        self.rate_limit_reset_time = 0
        self.rate_limit_remaining = 0
        self._authenticate()

    def _authenticate(self):
        try:
            response = requests.post(self.session_url, json={
                "identifier": self.username,
                "password": self.password
            })
            response.raise_for_status()
            self.jwt = response.json()["accessJwt"]
            logging.info("Successfully authenticated with Bluesky PDS.")
        except requests.exceptions.RequestException as e:
            logging.error(f"Authentication failed: {e}")
            raise

    def _check_rate_limit(self, response_headers):
        self.rate_limit_remaining = int(response_headers.get("RateLimit-Remaining", 1))
        self.rate_limit_reset_time = int(response_headers.get("RateLimit-Reset", time.time()))
        if self.rate_limit_remaining == 0:
            sleep_time = max(0, self.rate_limit_reset_time - time.time()) + 1 # Add 1 second buffer
            logging.warning(f"Rate limit hit. Sleeping for {sleep_time:.2f} seconds until reset.")
            time.sleep(sleep_time)
            self._authenticate() # Re-authenticate after rate limit to get fresh token if needed

    def search_posts(self, query: str, limit: int = 100, max_pages: int = 5) -> list:
        all_posts = []
        cursor = None
        headers = {"Authorization": f"Bearer {self.jwt}"}

        for page in tqdm(range(max_pages), desc=f"Searching for '{query}'"):
            params = {"q": query, "limit": limit}
            if cursor:
                params["cursor"] = cursor

            try:
                response = requests.get(self.search_url, headers=headers, params=params)
                self._check_rate_limit(response.headers)
                response.raise_for_status()
                data = response.json()
                posts = data.get("posts", [])
                if not posts:
                    break
                all_posts.extend(posts)
                cursor = data.get("cursor")
                if not cursor:
                    break
                time.sleep(1) # Small delay between pages
            except requests.exceptions.RequestException as e:
                logging.error(f"Error during search for '{query}': {e}")
                break
            except Exception as e:
                logging.error(f"An unexpected error occurred: {e}")
                break
        return all_posts

def main():
    parser = argparse.ArgumentParser(description="Search Bluesky posts for specific phrases.")
    parser.add_argument(
        "--query",
        type=str,
        required=True,
        help="The exact phrase to search for in Bluesky posts."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of posts to retrieve per API request (max 100). Default: 100"
    )
    parser.add_argument(
        "--max_pages",
        type=int,
        default=5,
        help="Maximum number of pages to fetch. Each page fetches 'limit' posts. Default: 5"
    )
    parser.add_argument(
        "--output_file",
        type=str,
        default="bluesky_search_results.json",
        help="Output JSON file to save the search results. Default: bluesky_search_results.json"
    )
    args = parser.parse_args()

    if not BSKY_USERNAME or not BSKY_PASSWORD:
        logging.error("Bluesky username or password not found in .env file.")
        return

    try:
        client = BlueskySearchClient(BSKY_PDS_URL, BSKY_USERNAME, BSKY_PASSWORD)
        logging.info(f"Starting search for query: '{args.query}'")
        posts = client.search_posts(args.query, args.limit, args.max_pages)
        logging.info(f"Found {len(posts)} posts matching '{args.query}'.")

        with open(args.output_file, 'w', encoding='utf-8') as f:
            json.dump(posts, f, indent=2, ensure_ascii=False)
        logging.info(f"Search results saved to {args.output_file}")

    except Exception as e:
        logging.error(f"An error occurred during the search: {e}")

if __name__ == "__main__":
    main()
