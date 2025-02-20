import os
import requests
import logging
import pandas as pd
from db import get_db_connection, close_db_connection
# Import the EquityToken model (adjust the import path as needed)
from models import EquityToken

logger = logging.getLogger(__name__)

def download_nse_csv(url, file_name):
    """
    Fetches a CSV file from the given URL and saves it to the specified directory.
    If file_name is "ALL", token data is inserted into the DB.
    """
    try:
        # Ensure the data directory exists
        save_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data"
        )
        os.makedirs(save_dir, exist_ok=True)

        file_name_with_format = f"{file_name}.csv"
        file_path = os.path.join(save_dir, file_name_with_format)

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            ),
            "Accept": "text/csv,application/json,application/xml,*/*;q=0.9",
        }

        logger.info(f"Fetching file from: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        # Write file content to disk
        with open(file_path, "wb") as file:
            file.write(response.content)

        logger.info(f"File saved successfully at: {file_path}")

        # Choose the insert method based on file_name
        if file_name == "ALL":
            insert_token_data_all(file_path, file_name)
        else:
            insert_token_data(file_path, file_name)

    except requests.exceptions.Timeout:
        logger.error(f"Error: Request timed out while trying to access {url}")
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred: {http_err}")
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Error: An error occurred while fetching the file - {req_err}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")


def insert_token_data_all(file_path, segment):
    """
    Reads the downloaded CSV file and inserts token data into the DB.
    Assumes the CSV columns are:
      SYMBOL, NAME OF COMPANY, SERIES, DATE OF LISTING, PAID UP VALUE,
      MARKET LOT, ISIN NUMBER, FACE VALUE
    """
    conn, cur = get_db_connection()
    try:
        # Read CSV with explicit delimiter and rename columns
        df = pd.read_csv(file_path, sep=",", engine="python")
        df.columns = [
            'tradingsymbol', 'Company Name', 'Series', 'Date of Listing',
            'Paid Up Value', 'Market Lot', 'ISIN Number', 'Face Value'
        ]

        # Delete existing tokens for this segment
        EquityToken.delete_by_segment(cur, segment)
        logger.info(f"Deleted all instruments for segment '{segment}' from equity_tokens.")

        # Fetch data from equity_instruments to merge
        select_query = "SELECT * FROM equity_instruments;"
        cur.execute(select_query)
        all_inst_df = pd.DataFrame(
            cur.fetchall(),
            columns=[
                'instrument_token', 'exchange_token', 'tradingsymbol', 'name',
                'last_price', 'tick_size', 'instrument_type', 'segment',
                'exchange'
            ]
        )

        # Merge CSV data with instruments from the DB on tradingsymbol
        filtered_df = pd.merge(df, all_inst_df, on='tradingsymbol', how='left')
        # Drop rows missing critical fields
        filtered_df = filtered_df.dropna(subset=['instrument_token', 'exchange'])

        # Convert columns to proper types
        filtered_df['instrument_token'] = filtered_df['instrument_token'].astype(int)
        filtered_df['tradingsymbol'] = filtered_df['tradingsymbol'].astype(str)
        filtered_df['Company Name'] = filtered_df['Company Name'].astype(str)
        filtered_df['exchange'] = filtered_df['exchange'].astype(str)

        # Build a list of EquityToken objects
        tokens_to_insert = []
        for _, row in filtered_df.iterrows():
            eq_token = EquityToken(
                instrument_token=row['instrument_token'],
                tradingsymbol=row['tradingsymbol'],
                company_name=row['Company Name'],
                exchange=row['exchange'],
                segment=segment
            )
            tokens_to_insert.append(eq_token)

        # Insert them at once
        EquityToken.save_many(cur, tokens_to_insert)
        conn.commit()

        logger.info(f"Inserted {len(tokens_to_insert)} records into equity_tokens.")

    except Exception as e:
        logger.error(f"An error occurred in insert_token_data_all: {e}")
        conn.rollback()
    finally:
        if conn and cur:
            close_db_connection()


def insert_token_data(file_path, segment):
    """
    Reads the downloaded CSV file and inserts token data into the DB.
    Assumes the CSV columns are:
      Company Name, Industry, tradingsymbol, Series, ISIN Code
    """
    conn, cur = get_db_connection()
    try:
        # Read the CSV
        df = pd.read_csv(file_path)
        df.columns = ['Company Name', 'Industry', 'tradingsymbol', 'Series', 'ISIN Code']

        # Delete existing tokens for this segment
        EquityToken.delete_by_segment(cur, segment)
        logger.info(f"Deleted all instruments for segment '{segment}' from equity_tokens.")

        # Fetch data from equity_instruments to merge
        select_query = "SELECT * FROM equity_instruments;"
        cur.execute(select_query)
        all_inst_df = pd.DataFrame(
            cur.fetchall(),
            columns=[
                'instrument_token', 'exchange_token', 'tradingsymbol', 'name',
                'last_price', 'tick_size', 'instrument_type', 'segment',
                'exchange'
            ]
        )

        # Merge CSV data with instruments from the DB on tradingsymbol
        filtered_df = pd.merge(df, all_inst_df, on='tradingsymbol', how='left')
        filtered_df = filtered_df.dropna(subset=['instrument_token', 'exchange'])

        # Convert columns to proper types
        filtered_df['instrument_token'] = filtered_df['instrument_token'].astype(int)
        filtered_df['tradingsymbol'] = filtered_df['tradingsymbol'].astype(str)
        filtered_df['Company Name'] = filtered_df['Company Name'].astype(str)
        filtered_df['exchange'] = filtered_df['exchange'].astype(str)

        # Build a list of EquityToken objects
        tokens_to_insert = []
        for _, row in filtered_df.iterrows():
            eq_token = EquityToken(
                instrument_token=row['instrument_token'],
                tradingsymbol=row['tradingsymbol'],
                company_name=row['Company Name'],
                exchange=row['exchange'],
                segment=segment
            )
            tokens_to_insert.append(eq_token)

        # Insert them at once
        EquityToken.save_many(cur, tokens_to_insert)
        conn.commit()

        logger.info(f"Inserted {len(tokens_to_insert)} records into equity_tokens.")

    except Exception as e:
        logger.error(f"An error occurred in insert_token_data: {e}")
        conn.rollback()
    finally:
        if conn and cur:
            close_db_connection()
