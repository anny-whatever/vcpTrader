import datetime
import time
import pandas as pd
import pandas_ta as ta
from controllers import kite
from db import get_db_connection, close_db_connection
import pytz  # Import for timezone handling

# Define the desired timezone
TIMEZONE = pytz.timezone("Asia/Kolkata")
ohlc_data = None

def load_ohlc_data():
    """
    Fetch OHLC data from the database and convert Decimal values to float.

    Returns:
        pd.DataFrame: DataFrame containing OHLC data.
    """
    conn, cur = get_db_connection()
    try:
        query = "SELECT * FROM ohlc"
        cur.execute(query)
        data = cur.fetchall()
        
        # Convert data to DataFrame
        df = pd.DataFrame(data, columns=["instrument_token", "symbol", "interval", "date", "open", "high", "low", "close", "volume", "segment"])
        
        # Convert Decimal columns to float
        decimal_columns = ["open", "high", "low", "close", "volume"]
        for col in decimal_columns:
            df[col] = df[col].astype(float)
        
        df["date"] = pd.to_datetime(df["date"])  # Ensure date is in datetime format
        return df
    except Exception as err:
        print(f"Error fetching OHLC data: {err}")
        return pd.DataFrame()
    finally:
        close_db_connection()


def fetch_live_quotes():
    """
    Fetch live quote data for all instrument tokens from the equity_tokens table.

    Returns:
        dict: A dictionary mapping instrument_tokens to their last_price.
    """
    conn, cur = get_db_connection()
    try:
        query = "SELECT instrument_token FROM equity_tokens;"
        cur.execute(query)
        tokens = cur.fetchall()
        instrument_tokens = [int(token[0]) for token in tokens]
        live_quotes = kite.quote(instrument_tokens)
        return {int(token): live_quotes[token]["last_price"] for token in live_quotes}
    except Exception as err:
        print(f"Error fetching live quotes: {err}")
        return {}
    finally:
        close_db_connection()

def calculate_smas(ohlc_data, live_data={}):
    updated_data = []
    
    for instrument_token, group in ohlc_data.groupby("instrument_token"):
        if instrument_token in live_data:
            live_price = live_data[instrument_token]
            last_row = group.iloc[-1]
            new_row = {
                "instrument_token": instrument_token,
                "symbol": last_row["symbol"],
                "interval": last_row["interval"],
                "date": datetime.datetime.now(TIMEZONE),
                "open": last_row["close"],
                "high": max(last_row["close"], live_price),
                "low": min(last_row["close"], live_price),
                "close": live_price,
                "volume": 0,
                "segment": last_row["segment"]
            }
            group = pd.concat([group, pd.DataFrame([new_row])], ignore_index=True)

        # Calculate SMAs
        group["sma_50"] = ta.sma(group["close"], length=min(50, len(group)))
        group["sma_150"] = ta.sma(group["close"], length=min(150, len(group)))
        group["sma_200"] = ta.sma(group["close"], length=min(200, len(group)))
        group['atr'] = ta.atr(group['high'], group['low'], group['close'], length=min(50, len(group)))
        group["52_week_high"] = group['high'].rolling(window=min(252, len(group)), min_periods=1).max()
        group["52_week_low"] = group['low'].rolling(window=min(252, len(group)), min_periods=1).min()
        group['away_from_high'] = ((group['52_week_high'] - group['close']) / group['52_week_high']) * 100
        group['away_from_low'] = ((group['close'] - group['52_week_low']) / group['52_week_low']) * 100

        # Fill NaN values with defaults
        group = group.fillna({
            "sma_50": 0,
            "sma_150": 0,
            "sma_200": 0,
            "atr": 0,
            "52_week_high": 0,
            "52_week_low": 0,
            "away_from_high": 0,
            "away_from_low": 0
        })

        updated_data.append(group)

    return pd.concat(updated_data, ignore_index=True)


def screen_eligible_stocks_vcp():
    """
    Screen eligible stocks based on calculated SMAs.

    Returns:
        list: List of eligible stocks with instrument_token and symbol.
    """
    
    global ohlc_data
    if ohlc_data is None:
        ohlc_data = load_ohlc_data()
    
    START_TIME = datetime.time(9, 15)
    END_TIME = datetime.time(15, 30, 5)
    now = datetime.datetime.now().time()
    if START_TIME <= now <= END_TIME:
        live_data = fetch_live_quotes()
    else:
        live_data = {}

    if ohlc_data.empty:
        print("No data available for screening.")
        return []

    updated_data = ohlc_data[ohlc_data['segment'] != 'IPO']
    updated_data = calculate_smas(ohlc_data, live_data)

    # Screen stocks based on conditions
    eligible_stocks = []
    for symbol, group in updated_data.groupby("symbol"):
        group = group.sort_values("date").reset_index(drop=True)
        last_index = len(group) - 1

        # Check conditions for eligibility
        if (
            group.iloc[last_index]["close"] > group.iloc[last_index]["sma_50"] and
            group.iloc[last_index]["sma_50"] > group.iloc[last_index]["sma_150"] > group.iloc[last_index]["sma_200"] and
            group.iloc[max(0, last_index - 110)]["sma_200"] < group.iloc[last_index]["sma_200"] and 
            group.iloc[last_index]["away_from_high"] < 25 and
            group.iloc[last_index]["away_from_low"] > 50
        ):
            eligible_stocks.append({
                "instrument_token": int(group.iloc[last_index]["instrument_token"]),
                "symbol": symbol,
                "last_price": float(group.iloc[last_index]["close"]),
                "change": ((float(group.iloc[last_index]["close"]) - float(group.iloc[last_index - 1]["close"]))/float(group.iloc[last_index - 1]["close"]))*100,
                "sma_50": float(group.iloc[last_index]["sma_50"]),
                "sma_150": float(group.iloc[last_index]["sma_150"]),
                "sma_200": float(group.iloc[last_index]["sma_200"]),
                "atr": float(group.iloc[last_index]["atr"]),
            })

    return eligible_stocks

def screen_eligible_stocks_ipo():
    
    global ohlc_data
    if ohlc_data is None:
        ohlc_data = load_ohlc_data()
    
    START_TIME = datetime.time(9, 15)
    END_TIME = datetime.time(15, 30, 5)
    now = datetime.datetime.now().time()
    if START_TIME <= now <= END_TIME:
        live_data = fetch_live_quotes()
    else:
        live_data = {}

    if ohlc_data.empty:
        print("No data available for screening.")
        return []    
    
    updated_data = ohlc_data[ohlc_data['segment'] == 'IPO']
    updated_data = calculate_smas(updated_data, live_data)
    
    # Screen stocks based on conditions
    eligible_stocks = []

        # Check conditions for eligibility
    for symbol, group in updated_data.groupby("symbol"):
        group = group.sort_values("date").reset_index(drop=True)
        last_index = len(group) - 1
        
        if (
            
            group.iloc[last_index]["away_from_high"] < 25 and
            group.iloc[last_index]["away_from_low"] > 25
        ):
            eligible_stocks.append({
                "instrument_token": int(group.iloc[last_index]["instrument_token"]),
                "symbol": symbol,
                "last_price": float(group.iloc[last_index]["close"] or 0),
                "change": ((float(group.iloc[last_index]["close"]) - float(group.iloc[last_index - 1]["close"]))/float(group.iloc[last_index - 1]["close"]))*100,
                "sma_50": float(group.iloc[last_index]["sma_50"] or 0),
                "sma_150": float(group.iloc[last_index]["sma_150"] or 0),
                "sma_200": float(group.iloc[last_index]["sma_200"] or 0),
                "atr": float(group.iloc[last_index]["atr"] or 0),
            })
    
    return eligible_stocks