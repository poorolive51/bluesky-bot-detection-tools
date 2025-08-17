import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import logging
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def visualize_spammer_activity(input_csv: str, output_image: str):
    """
    Creates a timeline visualization of spammer activity from a CSV file.
    The input CSV is expected to have 'timestamp' and 'handle' columns.
    """
    try:
        df = pd.read_csv(input_csv)
        if 'timestamp' not in df.columns or 'handle' not in df.columns:
            logging.error(f"Error: Input CSV '{input_csv}' must contain 'timestamp' and 'handle' columns.")
            return

        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')

        # Aggregate activity by handle and time (e.g., daily)
        df['date'] = df['timestamp'].dt.date
        activity_counts = df.groupby(['date', 'handle']).size().reset_index(name='post_count')

        plt.figure(figsize=(15, 8))
        sns.lineplot(data=activity_counts, x='date', y='post_count', hue='handle', marker='o')

        plt.title('Spammer Activity Over Time')
        plt.xlabel('Date')
        plt.ylabel('Number of Posts')
        plt.xticks(rotation=45)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()

        plt.savefig(output_image)
        logging.info(f"Spammer activity visualization saved to '{output_image}'.")

    except FileNotFoundError:
        logging.error(f"Error: Input CSV file '{input_csv}' not found.")
    except Exception as e:
        logging.error(f"An error occurred during visualization: {e}")

def main():
    parser = argparse.ArgumentParser(description="Visualize Bluesky spammer activity from a CSV file.")
    parser.add_argument(
        "--input_csv",
        type=str,
        required=True,
        help="Path to the input CSV file containing spammer activity (must have 'timestamp' and 'handle' columns)."
    )
    parser.add_argument(
        "--output_image",
        type=str,
        default="spammer_activity_timeline.png",
        help="Output image file to save the visualization. Default: spammer_activity_timeline.png"
    )
    args = parser.parse_args()

    visualize_spammer_activity(args.input_csv, args.output_image)

if __name__ == "__main__":
    main()
