import os
import requests
import logging
from datetime import datetime
import pandas as pd
from db import get_db_connection, close_db_connection

logger = logging.getLogger(__name__)

def download_nse_csv(url, file_name):
    """
    Fetches a CSV file from the given URL and saves it to the specified directory.
    """
    try:
        save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
        os.makedirs(save_dir, exist_ok=True)
        file_name_with_format = f"{file_name}.csv"
        file_path = os.path.join(save_dir, file_name_with_format)
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            ),
            "Accept": "text/csv,application/json,application/xml,*/*;q=0.9",
        }
        logger.info(f"Fetching file from: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()  # Raise HTTPError for bad responses
        with open(file_path, "wb") as file:
            file.write(response.content)
        logger.info(f"File saved successfully at: {file_path}")
        insert_token_data(file_path, file_name)
    except requests.exceptions.Timeout:
        logger.error(f"Error: Request timed out while trying to access {url}")
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred: {http_err}")
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Error: An error occurred while fetching the file - {req_err}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")

def insert_token_data(file_path, segment):
    conn, cur = get_db_connection()
    try:
        df = pd.read_csv(file_path)
        df.columns = ['Company Name', 'Industry', 'tradingsymbol', 'Series', 'ISIN Code']
        select_query = """SELECT * FROM equity_instruments;"""
        cur.execute(select_query)
        all_inst_df = pd.DataFrame(
            cur.fetchall(),
            columns=[
                'instrument_token', 'exchange_token', 'tradingsymbol', 'name',
                'last_price', 'tick_size', 'instrument_type', 'segment', 'exchange'
            ]
        )
        filtered_df = pd.merge(df, all_inst_df, on='tradingsymbol', how='left')
        filtered_df = filtered_df.dropna(subset=['instrument_token', 'exchange'])
        filtered_df['instrument_token'] = filtered_df['instrument_token'].astype(int)
        filtered_df['tradingsymbol'] = filtered_df['tradingsymbol'].astype(str)
        filtered_df['Company Name'] = filtered_df['Company Name'].astype(str)
        filtered_df['exchange'] = filtered_df['exchange'].astype(str)
        insert_query = """
        INSERT INTO equity_tokens (instrument_token, tradingsymbol, company_name, exchange, segment)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (tradingsymbol, instrument_token) DO NOTHING;
        """
        data_to_insert = []
        for _, row in filtered_df.iterrows():
            data_to_insert.append((
                row['instrument_token'],
                row['tradingsymbol'],
                row['Company Name'],
                row['exchange'],
                segment
            ))
        logger.info(f"Inserting token data: {data_to_insert}")
        cur.executemany(insert_query, data_to_insert)
        conn.commit()
    except Exception as e:
        logger.error(f"An error occurred in insert_token_data: {e}")
        conn.rollback()
    finally:
        close_db_connection()
