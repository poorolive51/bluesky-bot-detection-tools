import os
import time
import pandas as pd
from atproto import Client, models
from dotenv import load_dotenv
import logging
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

# Bluesky credentials
BSKY_USERNAME = os.getenv("BSKY_USERNAME")
BSKY_PASSWORD = os.getenv("BSKY_PASSWORD")

def get_all_replies(client: Client, actor_did: str) -> list:
    """
    Fetches all replies made by a specific actor (user DID).
    """
    all_replies = []
    cursor = None
    while True:
        try:
            response = client.app.bsky.feed.search_posts(
                q=f"from:{actor_did} reply",
                cursor=cursor,
                limit=100  # Max limit per request
            )
            posts = response.posts
            if not posts:
                break
            all_replies.extend(posts)
            cursor = response.cursor
            if not cursor:
                break
            time.sleep(0.5)  # Be kind to the API
        except Exception as e:
            logging.error(f"Error fetching replies for {actor_did}: {e}")
            break
    return all_replies

def analyze_reply_timing(replies: list) -> pd.DataFrame:
    """
    Analyzes the timing patterns between a user's replies.
    """
    if not replies:
        return pd.DataFrame()

    # Extract timestamps and sort them
    timestamps = []
    for post in replies:
        try:
            # Ensure the post is a valid record and has a createdAt field
            if isinstance(post.record, models.AppBskyFeedPost.Record) and post.record.created_at:
                timestamps.append(pd.to_datetime(post.record.created_at))
        except Exception as e:
            logging.warning(f"Could not parse timestamp for a post: {e}")
            continue

    if not timestamps:
        return pd.DataFrame()

    timestamps.sort()

    # Calculate time differences between consecutive replies
    time_diffs = [timestamps[i] - timestamps[i-1] for i in range(1, len(timestamps))]

    # Convert timedelta to seconds for easier analysis
    time_diffs_seconds = [td.total_seconds() for td in time_diffs]

    df = pd.DataFrame({'time_diff_seconds': time_diffs_seconds})

    # Basic statistics
    logging.info(f"\nReply Timing Analysis (seconds):\n{df.describe()}")

    return df

def main():
    parser = argparse.ArgumentParser(description="Analyze Bluesky user reply timing patterns.")
    parser.add_argument(
        "--handle",
        type=str,
        required=True,
        help="The Bluesky handle (e.g., 'user.bsky.social') of the user to analyze."
    )
    args = parser.parse_args()

    if not BSKY_USERNAME or not BSKY_PASSWORD:
        logging.error("Bluesky username or password not found in .env file.")
        return

    client = Client()
    try:
        client.login(args.handle, BSKY_PASSWORD)
        logging.info(f"Successfully logged in as {args.handle}")
    except Exception as e:
        logging.error(f"Failed to log in: {e}")
        return

    # Resolve handle to DID
    try:
        profile = client.app.bsky.actor.get_profile(actor=args.handle)
        actor_did = profile.did
        logging.info(f"Resolved handle {args.handle} to DID: {actor_did}")
    except Exception as e:
        logging.error(f"Could not resolve DID for handle {args.handle}: {e}")
        return

    logging.info(f"Fetching all replies for {args.handle}...")
    replies = get_all_replies(client, actor_did)
    logging.info(f"Found {len(replies)} replies for {args.handle}.")

    if replies:
        df_timing = analyze_reply_timing(replies)
        if not df_timing.empty:
            logging.info("Reply timing analysis complete.")
            # You can add more visualization or saving logic here if needed
        else:
            logging.info("No valid reply timestamps found for analysis.")
    else:
        logging.info("No replies found to analyze.")

if __name__ == "__main__":
    main()
