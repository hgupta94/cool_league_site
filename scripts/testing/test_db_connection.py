import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from scripts.utils.database import Database
import pandas as pd


def test_connection(use_ssh: bool):
    print(f"\nTesting {'SSH' if use_ssh else 'local'} connection...")
    try:
        with Database(table=None, use_ssh=use_ssh) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DATABASE();")
            db_name = cursor.fetchone()
            print(f"Connected! Database name: {db_name[0]}")
    except Exception as e:
        print(f"Connection failed: {e}")


def test_pull_records():
    print("\nTesting SSH data pull from 'records' table...")
    try:
        with Database(table='records', use_ssh=True) as conn:
            df = pd.read_sql('SELECT * FROM records;', conn)
            print(f"Pulled {len(df)} rows from 'records'. Sample:")
            print(df.head())
    except Exception as e:
        print(f"Data pull failed: {e}")


def main():
    print("Testing database connections...")
    # test_connection(use_ssh=False)
    test_connection(use_ssh=True)


if __name__ == "__main__":
    main()
    test_pull_records()
