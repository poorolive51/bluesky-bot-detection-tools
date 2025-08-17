import os
import json
import csv
from datetime import datetime
from dotenv import load_dotenv
import logging
import argparse

from atproto import CAR, AtUri, Client, models, parse_subscribe_labels_message

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

# Bluesky credentials (for resolving DIDs to handles)
BSKY_USERNAME = os.getenv("BSKY_USERNAME")
BSKY_PASSWORD = os.getenv("BSKY_PASSWORD")

def write_spam_label(handle: str, timestamp: str, output_csv: str):
    """
    Writes detected spam labels to a CSV file.
    """
    file_exists = os.path.isfile(output_csv)
    with open(output_csv, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['handle', 'timestamp'])
        writer.writerow([handle, timestamp])

def resolve_did_to_handle(client: Client, did: str) -> str:
    """
    Resolves a DID to a Bluesky handle.
    """
    try:
        profile = client.app.bsky.actor.get_profile(actor=did)
        return profile.handle
    except Exception as e:
        logging.warning(f"Could not resolve DID {did} to handle: {e}")
        return did # Return DID if handle resolution fails

def subscribe_to_labels(output_csv: str, duration_seconds: int):
    """
    Subscribes to Bluesky label updates and logs spam labels.
    """
    client = Client()
    if BSKY_USERNAME and BSKY_PASSWORD:
        try:
            client.login(BSKY_USERNAME, BSKY_PASSWORD)
            logging.info(f"Successfully logged in as {BSKY_USERNAME} for DID resolution.")
        except Exception as e:
            logging.warning(f"Failed to log in for DID resolution: {e}. Will proceed without handle resolution.")
            client = None # Set client to None if login fails
    else:
        logging.warning("Bluesky username or password not found. Will proceed without handle resolution.")
        client = None

    logging.info(f"Subscribing to Bluesky label firehose for {duration_seconds} seconds...")
    start_time = datetime.now()

    # The Bluesky firehose endpoint for labels
    # This might need to be adjusted if the ATProto SDK changes how it handles label subscriptions
    # For atproto 0.10.0+, it's typically client.subscribe_labels
    
    # This part assumes a direct WebSocket connection or a high-level SDK function.
    # The `atproto` library's `subscribe_labels` is the correct way.
    # The original gist might have used a lower-level approach or an older SDK version.
    # We'll use the current recommended way.

    try:
        for message in client.subscribe_labels():
            if (datetime.now() - start_time).total_seconds() > duration_seconds:
                logging.info("Subscription duration ended.")
                break

            parsed_message = parse_subscribe_labels_message(message)

            if isinstance(parsed_message, models.ComAtprotoLabelSubscribeLabels.Labels):
                for label in parsed_message.labels:
                    if label.val == 'spam':
                        uri = AtUri.from_str(label.uri)
                        handle_or_did = uri.host
                        
                        # Resolve DID to handle if client is available
                        if client and handle_or_did.startswith('did:'):
                            resolved_handle = resolve_did_to_handle(client, handle_or_did)
                            logging.info(f"Detected spam label for DID: {handle_or_did}, resolved to handle: {resolved_handle}")
                            write_spam_label(resolved_handle, label.cts, output_csv)
                        else:
                            logging.info(f"Detected spam label for: {handle_or_did}")
                            write_spam_label(handle_or_did, label.cts, output_csv)

    except Exception as e:
        logging.error(f"Error subscribing to labels: {e}")

def main():
    parser = argparse.ArgumentParser(description="Subscribe to Bluesky label firehose to detect spam.")
    parser.add_argument(
        "--output_csv",
        type=str,
        default="spammers.csv",
        help="Output CSV file to save detected spammers. Default: spammers.csv"
    )
    parser.add_argument(
        "--duration_seconds",
        type=int,
        default=3600, # 1 hour
        help="Duration in seconds to subscribe to the firehose. Default: 3600 (1 hour)"
    )
    args = parser.parse_args()

    subscribe_to_labels(args.output_csv, args.duration_seconds)

if __name__ == "__main__":
    main()
