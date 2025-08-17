# Bluesky Bot Detection Tools

This repository contains Python scripts for detecting and analyzing automated accounts (bots) on Bluesky (AT Protocol) using its API and Firehose.

This project accompanies the blog post: [How to Trawl for Bots on Bluesky](https://medium.com/@poorolive51/how-to-trawl-for-bots-on-bluesky-f22221bac749)

## Overview

While platforms like Twitter have been extensively studied for bot activity, Bluesky also presents a growing ecosystem where automated accounts operate. This toolkit provides methods to identify and analyze such accounts.

## Prerequisites

Before you begin, ensure you have the following:

*   **Intermediate Python knowledge:** Familiarity with Python programming.
*   **Bluesky Account:** You will need a Bluesky account for authentication to access the API.
*   **Basic command-line familiarity:** For running the scripts.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/bluesky-bot-detection-tools.git
    cd bluesky-bot-detection-tools
    ```
    *(Note: You will need to create a new GitHub repository and push this code to it after I've finished creating the files.)*

2.  **Create a virtual environment (recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Bluesky Credentials:**
    Create a file named `.env` in the root directory of the project and add your Bluesky username and password as follows:

    ```
    BSKY_USERNAME="YOUR_BLUESKY_USERNAME"
    BSKY_PASSWORD="YOUR_BLUESKY_PASSWORD"
    ```
    **Important:** Remember to never commit your `.env` file to version control, as it contains sensitive credentials.

## Bot Detection Methods and Usage

This toolkit provides three primary methods for identifying bots:

All scripts now use Python's `logging` module for output, providing more structured information.

### Method 1: Searching the API for LLM-Generated Content

This method involves searching for exact phrases commonly used by Large Language Models (LLMs) but rarely by humans. Once potential bot accounts are identified, their reply patterns can be analyzed.

#### `bsky_search.py`
Searches for posts on Bluesky containing exact phrases.

**How to run:**
```bash
python bsky_search.py --query "the notion that" --max_pages 10 --output_file llm_posts.json
```
*   `--query` (required): The exact phrase to search for.
*   `--limit`: Maximum number of posts to retrieve per API request (default: 100).
*   `--max_pages`: Maximum number of pages to fetch (default: 5). Each page fetches `limit` posts.
*   `--output_file`: Output JSON file to save the search results (default: `bluesky_search_results.json`).

**Output:**
*   A JSON file containing the search results.

#### `bsky_reply_timeline.py`
Analyzes the timing patterns between a Bluesky user's replies.

**How to run:**
```bash
python bsky_reply_timeline.py --handle "example.bsky.social"
```
*   `--handle` (required): The Bluesky handle (e.g., `user.bsky.social`) of the user to analyze.

**Output:**
*   Logs showing statistics about reply timing (mean, median, etc.).

### Method 2: Looking for Coordinated Reposting

This method aims to identify engagement pods or coordinated amplification networks by detecting statistically unusual patterns in reposting behavior.

#### `sync_repost_detector.py`
Monitors the Bluesky WebSocket feed to detect synchronized reposting behavior among groups of users.

**How to run:**
```bash
python sync_repost_detector.py --duration_seconds 7200 --output_csv coordinated_reposts.csv --min_group_size 5 --min_shared_posts 5 --time_window_minutes 30
```
*   `--duration_seconds`: Duration in seconds to monitor the firehose (default: 3600, 1 hour).
*   `--output_csv`: Output CSV file to save detected synchronized repost groups (default: `synchronized_reposts.csv`).
*   `--min_group_size`: Minimum number of users in a group to be considered synchronized (default: 3).
*   `--min_shared_posts`: Minimum number of shared posts within the time window for a group to be considered synchronized (default: 4).
*   `--time_window_minutes`: Time window in minutes within which reposts must occur to be considered synchronized (default: 20).

**Output:**
*   A CSV file containing details of detected synchronized repost groups.

#### `reposter_filter.py`
Tracks reposts across a group of handles, reads handles from a CSV file, and writes group repost tracking results to a CSV file.

**How to run:**
```bash
python reposter_filter.py --input_csv handles_to_check.csv --output_csv filtered_reposts.csv
```
*   `--input_csv` (required): Path to the input CSV file containing Bluesky handles (must have a `handle` column).
*   `--output_csv`: Path to the output CSV file to save repost tracking results (default: `group_repost_results.csv`).

**Output:**
*   A CSV file with results of group repost tracking.

### Method 3: Piggybacking on the Bluesky Moderation Service

This method leverages Bluesky's moderation service, which publishes various labels (e.g., "spam," "scam," "inauthentic account"). By subscribing to the firehose for these labels, you can identify spammers.

#### `subscribe_labels.py`
Subscribes to label updates from Bluesky using a firehose connection, detects "spam" labels, and writes the handle and timestamp of spam posts to a CSV file.

**How to run:**
```bash
python subscribe_labels.py --duration_seconds 1800 --output_csv detected_spammers.csv
```
*   `--duration_seconds`: Duration in seconds to subscribe to the firehose (default: 3600, 1 hour).
*   `--output_csv`: Output CSV file to save detected spammers (default: `spammers.csv`).

**Output:**
*   A CSV file (`spammers.csv` by default) with the handle and timestamp of detected spam posts.

#### `spammer_activity_viz.py`
Creates a timeline visualization of spammer activity from a CSV file.

**How to run:**
```bash
python spammer_activity_viz.py --input_csv detected_spammers.csv --output_image spammer_timeline.png
```
*   `--input_csv` (required): Path to the input CSV file containing spammer activity (must have `timestamp` and `handle` columns).
*   `--output_image`: Output image file to save the visualization (default: `spammer_activity_timeline.png`).

**Output:**
*   A PNG image file showing the spammer activity timeline.

## Get the Code

All scripts mentioned in this tutorial are available in this repository.

## Contact

For questions or feedback, you can reach out to poorolive51@gmail.com.