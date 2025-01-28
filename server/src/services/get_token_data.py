import os
import requests
from datetime import datetime
import pandas as pd
from db import get_db_connection, close_db_connection


def download_nse_csv(url, file_name):
    """
    Fetches a CSV file from the given URL and saves it to the specified directory.
    """
    try:
        save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
        # Ensure the directory exists
        os.makedirs(save_dir, exist_ok=True)

        # Generate a file name if not provided
        file_name_with_format = f"{file_name}.csv"
        
        # Full path for the file
        file_path = os.path.join(save_dir, file_name_with_format)

        # Custom headers
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            ),
            "Accept": "text/csv,application/json,application/xml,*/*;q=0.9",
        }

        # Fetch the file
        print(f"Fetching file from: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx, 5xx)

        # Save the file
        with open(file_path, "wb") as file:
            file.write(response.content)

        
        insert_token_data(file_path, file_name)
        print(f"File saved successfully at: {file_path}")

    except requests.exceptions.Timeout:
        print(f"Error: Request timed out while trying to access {url}")
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"Error: An error occurred while fetching the file - {req_err}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def insert_token_data(file_path, segment):
    conn, cur = get_db_connection()
    try:
        # file_path = 'sml100.csv'

        df = pd.read_csv(file_path)

        # Rename columns
        df.columns = ['Company Name', 'Industry', 'tradingsymbol', 'Series', 'ISIN Code']

        # Fetch all instruments from the database
        select_query = """SELECT * FROM equity_instruments;"""
        cur.execute(select_query)

        all_inst_df = pd.DataFrame(
            cur.fetchall(),
            columns=[
                'instrument_token', 'exchange_token', 'tradingsymbol', 'name',
                'last_price', 'tick_size', 'instrument_type', 'segment', 'exchange'
            ]
        )

        # Merge DataFrames
        filtered_df = pd.merge(df, all_inst_df, on='tradingsymbol', how='left')


        # Create the table
        # create_table_query = """
        # CREATE TABLE IF NOT EXISTS equity_tokens (
        #     instrument_token INTEGER PRIMARY KEY,
        #     tradingsymbol VARCHAR(255),
        #     company_name VARCHAR(255),
        #     exchange VARCHAR(255),
        #     segment VARCHAR(255),
        #     CONSTRAINT unique_company_symbol UNIQUE (tradingsymbol, instrument_token)
        # );
        # """
        # cur.execute(create_table_query)
        # conn.commit()

        # Convert DataFrame columns to appropriate types
        filtered_df = filtered_df.dropna(subset=['instrument_token', 'exchange'])  # Remove rows with missing values
        filtered_df['instrument_token'] = filtered_df['instrument_token'].astype(int)
        filtered_df['tradingsymbol'] = filtered_df['tradingsymbol'].astype(str)
        filtered_df['Company Name'] = filtered_df['Company Name'].astype(str)
        filtered_df['exchange'] = filtered_df['exchange'].astype(str)
        

        # Batch insert into the database
        insert_query = """
        INSERT INTO equity_tokens (instrument_token, tradingsymbol, company_name, exchange, segment)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (tradingsymbol, instrument_token) DO NOTHING;
        """

        data_to_insert = []

        # Iterate over the rows of the DataFrame
        for _, row in filtered_df.iterrows():
            data_to_insert.append((
                row['instrument_token'],
                row['tradingsymbol'],
                row['Company Name'],
                row['exchange'],
                segment
            ))

        print(data_to_insert)
        cur.executemany(insert_query, data_to_insert)
        conn.commit()

    except Exception as e:
        print(f"An error occurred: {e}")
        conn.rollback()
    finally:
        close_db_connection()