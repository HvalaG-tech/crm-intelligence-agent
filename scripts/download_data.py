"""Download the Olist dataset from Kaggle into data/raw/.

Usage:
    python scripts/download_data.py

Requirements:
    pip install kaggle
    Set KAGGLE_USERNAME and KAGGLE_KEY environment variables
    or place ~/.kaggle/kaggle.json
"""

import subprocess
import sys
from pathlib import Path

RAW_DIR = Path("data/raw")


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print("Downloading Olist dataset from Kaggle…")
    result = subprocess.run(
        ["kaggle", "datasets", "download", "-d", "olistbr/brazilian-ecommerce",
         "--unzip", "-p", str(RAW_DIR)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("Error:", result.stderr)
        sys.exit(1)
    print(f"Downloaded to {RAW_DIR}/")
    print("Files:", [f.name for f in RAW_DIR.iterdir()])


if __name__ == "__main__":
    main()
