import logging
import pytz
from datetime import datetime, time
import pandas as pd
import pandas_ta as ta
import math
import numpy as np
from db import get_db_connection, close_db_connection
from models import PriceAlert, AlertMessage, RiskPool, SaveTradeDetails, SaveHistoricalTradeDetails, SaveOHLC, ScreenerResult
from controllers import kite  # Assumes you have a kite module for live quotes

logger = logging.getLogger(__name__)
TIMEZONE = pytz.timezone("Asia/Kolkata")
MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 35)

def safe_float(value, default=0.0):
    """
    Safely converts a value to float, returning a default if conversion fails.
    """
    try:
        if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default

def fetch_risk_pool_for_display():
    try:
        conn, cur = get_db_connection()
        risk_pool = RiskPool.fetch_risk_pool(cur)
        if risk_pool:
            return {
                "used_risk": safe_float(risk_pool.get('used_risk')),
                "available_risk": safe_float(risk_pool.get('available_risk'))
            }
        return None
    except Exception as e:
        logger.error(f"Error fetching risk pool for display: {e}")
        raise
    finally:
        if conn and cur:
            close_db_connection()

def format_trade_record(trade):
    return {
        "trade_id": trade['trade_id'],
        "stock_name": trade['stock_name'],
        "token": trade['token'],
        "entry_time": trade['entry_time'].isoformat() if trade['entry_time'] else None,
        "entry_price": safe_float(trade.get('entry_price')),
        "stop_loss": safe_float(trade.get('stop_loss')),
        "target": safe_float(trade.get('target')),
        "initial_qty": safe_float(trade.get('initial_qty')),
        "current_qty": safe_float(trade.get('current_qty')),
        "booked_pnl": safe_float(trade.get('booked_pnl')),
        "auto_exit": trade['auto_exit']
    }

def fetch_trade_details_for_display():
    try:
        conn, cur = get_db_connection()
        trade_details = SaveTradeDetails.fetch_all_trades(cur)
        if not trade_details:
            return []
        unique_tokens = list({trade['token'] for trade in trade_details})
        try:

            live_quotes = kite.quote(unique_tokens)
        except Exception as e:
            logger.error(f"Error fetching live quotes: {e}")
            live_quotes = {}
        formatted_trades = []
        for trade in trade_details:
            formatted = format_trade_record(trade)
            token_str = str(trade['token'])
            formatted['last_price'] = safe_float(live_quotes.get(token_str, {}).get('last_price', 0))
            formatted_trades.append(formatted)
        return formatted_trades
    except Exception as e:
        logger.error(f"Error in fetch_trade_details_for_display: {e}")
        raise
    finally:
        if conn and cur:
            close_db_connection()

def format_historical_trade_record(trade):
    return {
        "stock_name": trade['stock_name'],
        "entry_time": trade['entry_time'].isoformat() if trade['entry_time'] else None,
        "entry_price": safe_float(trade.get('entry_price')),
        "exit_time": trade['exit_time'].isoformat() if trade['exit_time'] else None,
        "exit_price": safe_float(trade.get('exit_price')),
        "final_pnl": safe_float(trade.get('final_pnl')),
        "highest_qty": safe_float(trade.get('highest_qty'))
    }

def fetch_historical_trade_details_for_display():
    try:
        conn, cur = get_db_connection()
        trade_details = SaveHistoricalTradeDetails.fetch_all_historical_trades(cur)
        return [format_historical_trade_record(trade) for trade in trade_details] if trade_details else []
    except Exception as e:
        logger.error(f"Error fetching historical trade details: {e}")
        raise
    finally:
        if conn and cur:
            close_db_connection()

def get_combined_ohlc(instrument_token, symbol, interval='day'):
    try:
        conn, cur = get_db_connection()
        
        # Fetch either daily or weekly data based on interval parameter
        if interval == 'week':
            historical_data = SaveOHLC.fetch_by_instrument_weekly(cur, instrument_token)
        else:  # Default to daily data
            historical_data = SaveOHLC.fetch_by_instrument(cur, instrument_token)
            
        combined_data = [dict(record) for record in historical_data] if historical_data else []
        now = datetime.now(TIMEZONE)
        today_date = now.date()
        
        # Handle live data updates
        if combined_data and MARKET_OPEN <= now.time() <= MARKET_CLOSE:
                try:
                # Fetch the current price for the instrument
                    quote = kite.quote(instrument_token)[str(instrument_token)]
                last_price = quote.get('last_price', 0)
                
                if interval == 'day':
                    # For daily charts - Add today's data if missing
                    last_historical_date = pd.to_datetime(combined_data[-1]['date']).astimezone(TIMEZONE).date()
                    if last_historical_date < today_date:
                        # Create a new daily candle for today
                        logger.info(f'Adding new daily candle for {symbol} with price {last_price}')
                    ohlc = quote.get('ohlc', {})
                    if ohlc:
                        today_entry = {
                            'instrument_token': instrument_token,
                            'symbol': symbol,
                            'interval': interval,
                            'date': TIMEZONE.localize(datetime.combine(today_date, time(15, 30))),
                            'open': ohlc.get('open', 0),
                            'high': ohlc.get('high', 0),
                            'low': ohlc.get('low', 0),
                                'close': last_price,
                            'volume': quote.get('volume_today', 0)
                        }
                        combined_data.append(today_entry)
                
                elif interval == 'week':
                    # For weekly charts - Update last candle or create new based on week
                    last_row = combined_data[-1]
                    last_date = pd.to_datetime(last_row['date']).to_pydatetime()
                    
                    # Import is_new_week from get_screener for consistency
                    from services.get_screener import is_new_week
                    
                    # Check if we need to create a new weekly candle or update existing
                    create_new_candle = is_new_week(last_date, now)
                    
                    if create_new_candle:
                        # Create a new weekly candle
                        logger.info(f'Creating NEW weekly candle for {symbol} with price {last_price}')
                        new_weekly_entry = {
                            'instrument_token': instrument_token,
                            'symbol': symbol,
                            'interval': 'week',
                            'date': now,
                            'open': last_price,  # For a new candle, open = current price
                            'high': last_price,
                            'low': last_price,
                            'close': last_price,
                            'volume': 0,
                            # Copy indicator values from previous candle as starting point
                            'sma_50': last_row.get('sma_50', 0),
                            'sma_150': last_row.get('sma_150', 0),
                            'sma_200': last_row.get('sma_200', 0),
                            'atr': last_row.get('atr', 0),
                            '52_week_high': last_row.get('52_week_high', 0),
                            '52_week_low': last_row.get('52_week_low', 0),
                            'away_from_high': last_row.get('away_from_high', 0),
                            'away_from_low': last_row.get('away_from_low', 0)
                        }
                        combined_data.append(new_weekly_entry)
                    else:
                        # Update the existing weekly candle
                        logger.info(f'Updating EXISTING weekly candle for {symbol} with price {last_price}')
                        last_row['high'] = max(last_row['high'], last_price)
                        last_row['low'] = min(last_row['low'], last_price)
                        last_row['close'] = last_price
                        # Note: we keep the original open price
                
                except Exception as e:
                    logger.error(f"Error fetching live data for {symbol}: {e}")
                    
        formatted_data = []
        for record in combined_data:
            formatted = record.copy()
            formatted['date'] = pd.to_datetime(formatted['date']).isoformat()
            for key in ['open', 'high', 'low', 'close', 'volume']:
                formatted[key] = safe_float(formatted.get(key))
            
            # Add indicators if they're not already in the data (weekly already has them)
            if interval == 'week':
                # These fields are already in the weekly data
                for key in ['sma_50', 'sma_150', 'sma_200', 'atr']:
                    if key in record:
                        formatted[key] = safe_float(record.get(key))
            
            formatted_data.append(formatted)
        
        # For daily data, we need to calculate SMAs (weekly already has them)
        if interval == 'day':
            df = pd.DataFrame(formatted_data)
            if not df.empty:
                df['sma_50'] = ta.sma(df['close'], length=min(50, len(df)))
                df['sma_150'] = ta.sma(df['close'], length=min(150, len(df)))
                df['sma_200'] = ta.sma(df['close'], length=min(200, len(df)))
                for col in ['sma_50', 'sma_150', 'sma_200']:
                    df[col] = df[col].replace([np.inf, -np.inf], np.nan)
                    df[col] = df[col].fillna(0)
                    df[col] = np.around(df[col], decimals=2)
                df = df.map(lambda x: 0 if isinstance(x, float) and not math.isfinite(x) else x)
                logger.info(f"get_combined_ohlc: returning {len(df)} rows of {interval} data")
                return df.to_dict(orient="records")
            else:
                return []
                
        # Weekly data already has all indicators computed
        logger.info(f"get_combined_ohlc: returning {len(formatted_data)} rows of {interval} data")
        return formatted_data
    except Exception as e:
        logger.error(f"Error in get_combined_ohlc for instrument {instrument_token}, symbol {symbol}, interval {interval}: {e}")
        raise
    finally:
        if conn and cur:
            close_db_connection()

def get_all_alerts():
    try:
        conn, cur = get_db_connection()
        alerts = PriceAlert.fetch_all_alerts(cur)
        if alerts is None:
            return []
        logger.info("All alerts fetched successfully.")
        return alerts
    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        return []
    finally:
        if conn and cur:
            close_db_connection()

def get_latest_alert_messages():
    try:
        conn, cur = get_db_connection()
        messages = AlertMessage.fetch_latest_messages(cur)
        if messages is None:
            return []
        logger.info("Latest alert messages fetched successfully.")
        return messages
    except Exception as e:
        logger.error(f"Error fetching latest alert messages: {e}")
        return []
    finally:
        if conn and cur:
            close_db_connection()

def fetch_screener_data(screener_name: str) -> list:
    """
    Fetch screener results from the screener_results table.
    Returns a list of dicts suitable for JSON response,
    sorted in descending order by 'change'.
    """
    logger.info(f"Fetching screener data for {screener_name}")
    conn, cur = get_db_connection()
    try:
        rows = ScreenerResult.fetch_by_screener(cur, screener_name)
        logger.info(f"Retrieved {len(rows)} rows for screener: {screener_name}")
        
        if not rows:
            logger.warning(f"No data found in screener_results for {screener_name}")
            return []
            
        data = []
        for row in rows:
            # row is (screener_name, instrument_token, symbol,
            #         last_price, change_pct, sma_50, sma_150,
            #         sma_200, atr, run_time)
            data.append({
                "screener_name": row[0],
                "instrument_token": row[1],
                "symbol": row[2],
                "last_price": safe_float(row[3]),
                "change": safe_float(row[4]),   # rename from 'change_pct' to 'change'
                "sma_50": safe_float(row[5]),
                "sma_150": safe_float(row[6]),
                "sma_200": safe_float(row[7]),
                "atr": safe_float(row[8]),
                "run_time": row[9].isoformat() if row[9] else None
            })

        # Sort the 'data' list in descending order by "change"
        data.sort(key=lambda x: x["change"], reverse=True)
        
        # Log some of the results
        if data:
            symbols = ", ".join([item["symbol"] for item in data[:5]])
            logger.info(f"Returning {len(data)} results for {screener_name}. First few symbols: {symbols}...")
        
        return data

    except Exception as e:
        logger.error(f"Error fetching screener data for {screener_name}: {e}")
        return []
    finally:
        close_db_connection()
