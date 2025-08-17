import os
import json
import time
import csv
from collections import defaultdict
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging
import argparse

from atproto import Client, models, parse_subscribe_repos_message

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

# Bluesky credentials (for resolving DIDs to handles)
BSKY_USERNAME = os.getenv("BSKY_USERNAME")
BSKY_PASSWORD = os.getenv("BSKY_PASSWORD")

class RepostMonitor:
    def __init__(self, min_group_size: int = 3, min_shared_posts: int = 4, time_window_minutes: int = 20):
        self.min_group_size = min_group_size
        self.min_shared_posts = min_shared_posts
        self.time_window = timedelta(minutes=time_window_minutes)
        self.repost_cache = defaultdict(lambda: defaultdict(list)) # {post_uri: {reposter_did: [timestamp, ...]}}
        self.client = Client()
        self.logged_in = False

        if BSKY_USERNAME and BSKY_PASSWORD:
            try:
                self.client.login(BSKY_USERNAME, BSKY_PASSWORD)
                self.logged_in = True
                logging.info(f"Successfully logged in as {BSKY_USERNAME} for DID resolution.")
            except Exception as e:
                logging.warning(f"Failed to log in for DID resolution: {e}. Will proceed without handle resolution.")
        else:
            logging.warning("Bluesky username or password not found. Will proceed without handle resolution.")

    def _resolve_did_to_handle(self, did: str) -> str:
        if self.logged_in:
            try:
                profile = self.client.app.bsky.actor.get_profile(actor=did)
                return profile.handle
            except Exception as e:
                logging.warning(f"Could not resolve DID {did} to handle: {e}")
        return did # Return DID if handle resolution fails or not logged in

    def _clean_cache(self):
        # Remove old entries from cache
        cutoff_time = datetime.now() - self.time_window
        posts_to_remove = []
        for post_uri, reposter_data in self.repost_cache.items():
            repost_data_to_keep = {}
            for reposter_did, timestamps in reposter_data.items():
                # Keep only timestamps within the window
                filtered_timestamps = [ts for ts in timestamps if ts > cutoff_time]
                if filtered_timestamps:
                    repost_data_to_keep[reposter_did] = filtered_timestamps
            
            if not repost_data_to_keep:
                posts_to_remove.append(post_uri)
            else:
                self.repost_cache[post_uri] = reposter_data_to_keep
        
        for post_uri in posts_to_remove:
            del self.repost_cache[post_uri]

    def process_repost(self, repo_did: str, record: models.AppBskyFeedRepost.Record, timestamp: str):
        post_uri = record.subject.uri.uri
        repost_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

        self.repost_cache[post_uri][repo_did].append(repost_time)
        self.repost_cache[post_uri][repo_did].sort() # Keep timestamps sorted

        self._clean_cache()

        # Check for synchronized reposts
        reposters = self.repost_cache[post_uri]
        if len(reposters) >= self.min_group_size:
            # Check if all reposts for this post_uri are within the time window
            all_timestamps = []
            for did, timestamps in reposters.items():
                all_timestamps.extend(timestamps)
            
            if all_timestamps:
                min_ts = min(all_timestamps)
                max_ts = max(all_timestamps)
                if (max_ts - min_ts) <= self.time_window:
                    # This post has been reposted by a group within the time window
                    # Now check if these group members have shared enough other posts
                    
                    # This part is complex and would require fetching more data for each group member
                    # to see their shared repost history. For now, we'll just log the group.
                    group_dids = list(reposters.keys())
                    group_handles = [self._resolve_did_to_handle(did) for did in group_dids]
                    logging.info(f"Detected potential synchronized repost group for post {post_uri}: {group_handles}")
                    # In a real scenario, you'd save this to a file or further analyze

    def listen_for_reposts(self, duration_seconds: int, output_csv: str):
        logging.info(f"Monitoring Bluesky firehose for synchronized reposts for {duration_seconds} seconds...")
        start_time = datetime.now()

        # Prepare CSV output
        file_exists = os.path.isfile(output_csv)
        output_file = open(output_csv, 'a', newline='', encoding='utf-8')
        csv_writer = csv.writer(output_file)
        if not file_exists:
            csv_writer.writerow(['post_uri', 'reposter_handles', 'repost_timestamps', 'group_size'])

        try:
            for message in self.client.subscribe_repos():
                if (datetime.now() - start_time).total_seconds() > duration_seconds:
                    logging.info("Subscription duration ended.")
                    break

                parsed_message = parse_subscribe_repos_message(message)

                if isinstance(parsed_message, models.ComAtprotoSyncSubscribeRepos.Commit):
                    for op in parsed_message.ops:
                        uri = AtUri.from_str(f"at://{parsed_message.repo}/{op.path}")
                        
                        if op.action == 'create' and uri.collection == models.ids.AppBskyFeedRepost:
                            # This is a new repost
                            try:
                                # Fetch the actual record to get the subject URI and timestamp
                                # This might be inefficient for a firehose, but necessary to get full repost info
                                # A more optimized approach would parse the record directly from the commit
                                # For simplicity, we'll assume the record is directly available or can be fetched.
                                # In atproto 0.10.0+, op.cid and op.record are available for created records.
                                
                                # Attempt to get the record from the message (if available)
                                record_bytes = None
                                for rec in parsed_message.blocks.values():
                                    if str(rec.cid) == str(op.cid):
                                        record_bytes = rec.value
                                        break
                                
                                if record_bytes:
                                    repost_record = models.AppBskyFeedRepost.Record.model_validate(record_bytes)
                                    self.process_repost(parsed_message.repo, repost_record, parsed_message.time)
                                else:
                                    logging.warning(f"Could not find record for repost {uri}")

                            except Exception as e:
                                logging.error(f"Error processing repost record: {e}")

        except Exception as e:
            logging.error(f"Error subscribing to repos: {e}")
        finally:
            output_file.close()
            logging.info(f"Synchronized repost detection finished. Results saved to {output_csv}")

def main():
    parser = argparse.ArgumentParser(description="Monitor Bluesky firehose for synchronized reposting behavior.")
    parser.add_argument(
        "--duration_seconds",
        type=int,
        default=3600, # 1 hour
        help="Duration in seconds to monitor the firehose. Default: 3600 (1 hour)"
    )
    parser.add_argument(
        "--output_csv",
        type=str,
        default="synchronized_reposts.csv",
        help="Output CSV file to save detected synchronized repost groups. Default: synchronized_reposts.csv"
    )
    parser.add_argument(
        "--min_group_size",
        type=int,
        default=3,
        help="Minimum number of users in a group to be considered synchronized. Default: 3"
    )
    parser.add_argument(
        "--min_shared_posts",
        type=int,
        default=4,
        help="Minimum number of shared posts within the time window for a group to be considered synchronized. Default: 4"
    )
    parser.add_argument(
        "--time_window_minutes",
        type=int,
        default=20,
        help="Time window in minutes within which reposts must occur to be considered synchronized. Default: 20"
    )
    args = parser.parse_args()

    monitor = RepostMonitor(args.min_group_size, args.min_shared_posts, args.time_window_minutes)
    monitor.listen_for_reposts(args.duration_seconds, args.output_csv)

if __name__ == "__main__":
    main()
