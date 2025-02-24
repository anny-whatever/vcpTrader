import logging
import pytz
from datetime import datetime, time
import pandas as pd
import pandas_ta as ta
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

def get_combined_ohlc(instrument_token, symbol):
    try:
        conn, cur = get_db_connection()
        historical_data = SaveOHLC.fetch_by_instrument(cur, instrument_token)
        combined_data = [dict(record) for record in historical_data] if historical_data else []
        now = datetime.now(TIMEZONE)
        today_date = now.date()
        if combined_data:
            last_historical_date = pd.to_datetime(combined_data[-1]['date']).astimezone(TIMEZONE).date()
            if last_historical_date < today_date and MARKET_OPEN <= now.time() <= MARKET_CLOSE and now.weekday() < 5:
                try:
                    quote = kite.quote(instrument_token)[str(instrument_token)]
                    logger.info(f'quote: {quote}')
                    ohlc = quote.get('ohlc', {})
                    if ohlc:
                        today_entry = {
                            'instrument_token': instrument_token,
                            'symbol': symbol,
                            'interval': 'day',
                            'date': TIMEZONE.localize(datetime.combine(today_date, time(15, 30))),
                            'open': ohlc.get('open', 0),
                            'high': ohlc.get('high', 0),
                            'low': ohlc.get('low', 0),
                            'close': quote.get('last_price', 0),
                            'volume': quote.get('volume_today', 0)
                        }
                        combined_data.append(today_entry)
                except Exception as e:
                    logger.error(f"Error fetching live data for {symbol}: {e}")
        formatted_data = []
        for record in combined_data:
            formatted = record.copy()
            formatted['date'] = pd.to_datetime(formatted['date']).isoformat()
            for key in ['open', 'high', 'low', 'close', 'volume']:
                formatted[key] = safe_float(formatted.get(key))
            formatted_data.append(formatted)
        
        df = pd.DataFrame(formatted_data)
        if not df.empty:
            df['sma_50'] = ta.sma(df['close'], length=min(50, len(df)))
            df['sma_150'] = ta.sma(df['close'], length=min(150, len(df)))
            df['sma_200'] = ta.sma(df['close'], length=min(200, len(df)))
            import numpy as np
            for col in ['sma_50', 'sma_150', 'sma_200']:
                df[col] = df[col].replace([np.inf, -np.inf], np.nan)
                df[col] = df[col].fillna(0)
                df[col] = np.around(df[col], decimals=2)
            import math
            df = df.map(lambda x: 0 if isinstance(x, float) and not math.isfinite(x) else x)
            logger.info(f"get_combined_ohlc: returning {len(df)} rows")
            return df.to_dict(orient="records")
        else:
            return []
    except Exception as e:
        logger.error(f"Error in get_combined_ohlc for instrument {instrument_token}, symbol {symbol}: {e}")
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
    conn, cur = get_db_connection()
    try:
        rows = ScreenerResult.fetch_by_screener(cur, screener_name)
        data = []
        for row in rows:
            # row is (screener_name, instrument_token, symbol,
            #         last_price, change_pct, sma_50, sma_150,
            #         sma_200, atr, run_time)
            data.append({
                "screener_name": row[0],
                "instrument_token": row[1],
                "symbol": row[2],
                "last_price": row[3],
                "change": row[4],   # rename from 'change_pct' to 'change'
                "sma_50": row[5],
                "sma_150": row[6],
                "sma_200": row[7],
                "atr": row[8],
                "run_time": row[9].isoformat() if row[9] else None
            })

        # Sort the 'data' list in descending order by "change"
        data.sort(key=lambda x: x["change"], reverse=True)

        return data

    except Exception as e:
        logger.error(f"Error fetching screener data for {screener_name}: {e}")
        return []
    finally:
        close_db_connection()
