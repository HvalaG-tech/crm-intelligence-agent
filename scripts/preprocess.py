"""Build processed parquets from raw Olist CSVs.

Usage:
    python scripts/preprocess.py
"""

from core.loader import OlistLoader


def main() -> None:
    print("Building canonical DataFrames from raw CSVs…")
    data = OlistLoader()._build_from_raw()
    for name, df in data.items():
        print(f"  {name}: {df.shape}")
    print("Processed files written to data/processed/")


if __name__ == "__main__":
    main()
