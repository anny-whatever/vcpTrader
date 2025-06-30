import logging
import pytz
from datetime import datetime, time
import pandas as pd
import pandas_ta as ta
import math
import numpy as np
from db import get_db_connection, close_db_connection
from models import PriceAlert, AlertMessage, RiskPool, SaveTradeDetails, SaveHistoricalTradeDetails, SaveOHLC, ScreenerResult, AdvancedVcpResult
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
        
        # Only add today's data for daily charts if market is open
        if interval == 'day' and combined_data:
            last_historical_date = pd.to_datetime(combined_data[-1]['date']).astimezone(TIMEZONE).date()
            if last_historical_date < today_date and MARKET_OPEN <= now.time() <= MARKET_CLOSE:
                try:
                    quote = kite.quote(instrument_token)[str(instrument_token)]
                    logger.info(f'quote: {quote}')
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
            
            # Add indicators if they're not already in the data (weekly already has them)
            if interval == 'week':
                # These fields are already in the weekly data
                for key in ['sma_50', 'sma_100', 'sma_200', 'atr']:
                    if key in record:
                        formatted[key] = safe_float(record.get(key))
            
            formatted_data.append(formatted)
        
        # For daily data, we need to calculate SMAs (weekly already has them)
        if interval == 'day':
            df = pd.DataFrame(formatted_data)
            if not df.empty:
                df['sma_50'] = ta.sma(df['close'], length=min(50, len(df)))
                df['sma_100'] = ta.sma(df['close'], length=min(100, len(df)))
                df['sma_200'] = ta.sma(df['close'], length=min(200, len(df)))
                for col in ['sma_50', 'sma_100', 'sma_200']:
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
    Fetch screener results. For 'vcp', it gets data from the new advanced
    results table and enhances it with live quote data. For others, it uses the old table with risk scores.
    """
    logger.info(f"Fetching screener data for {screener_name}")
    conn, cur = get_db_connection()
    try:
        if screener_name == "vcp":
            # Fetch from the new, comprehensive advanced_vcp_results table
            results = AdvancedVcpResult.fetch_all(cur)
            logger.info(f"Retrieved {len(results)} rows for screener: {screener_name} from advanced table.")
            
            if not results:
                return []
            
            # Enhance with live quote data during market hours
            enhanced_results = []
            try:
                # Check if market is open
                import datetime
                import pytz
                TIMEZONE = pytz.timezone("Asia/Kolkata")
                START_TIME = datetime.time(9, 15)
                END_TIME = datetime.time(15, 30, 5)
                now = datetime.datetime.now(TIMEZONE).time()
                
                # Collect unique instrument tokens from the screener results
                unique_tokens = list({result['instrument_token'] for result in results if result.get('instrument_token') and result.get('instrument_token') != -1})
                
                # Fetch live quotes for all tokens (try regardless of market hours for live data updates)
                live_quotes = {}
                if unique_tokens:
                    try:
                        from controllers import kite
                        live_quotes = kite.quote(unique_tokens)
                        logger.info(f"Fetched live quotes for {len(live_quotes)} screener stocks")
                    except Exception as quote_error:
                        logger.error(f"Error fetching quotes for screener stocks: {quote_error}")
                
                # Process each result and enhance with live data
                for result in results:
                    enhanced_result = result.copy()
                    token_str = str(result.get('instrument_token', ''))
                    quote_data = live_quotes.get(token_str, {})
                    
                    if quote_data:
                        # Update with live price
                        enhanced_result['last_price'] = float(quote_data.get('last_price', result.get('entry_price', 0)))
                        enhanced_result['current_price'] = enhanced_result['last_price']
                        
                        # Calculate percentage change from live data
                        ohlc = quote_data.get('ohlc', {})
                        prev_close = ohlc.get('close', 0)
                        current_price = enhanced_result['last_price']
                        
                        if prev_close and prev_close != 0:
                            change_pct = ((current_price - prev_close) / prev_close) * 100
                            enhanced_result['change'] = round(change_pct, 2)
                        else:
                            # Fallback to stored change_pct or 0
                            enhanced_result['change'] = result.get('change_pct', 0)
                        
                        # Include additional live data
                        enhanced_result['ohlc'] = ohlc
                        enhanced_result['volume_today'] = quote_data.get('volume_today', 0)
                    else:
                        # No live data available, use stored values
                        enhanced_result['last_price'] = result.get('entry_price', 0)
                        enhanced_result['current_price'] = enhanced_result['last_price']
                        enhanced_result['change'] = result.get('change_pct', 0)
                    
                    enhanced_results.append(enhanced_result)
                
                logger.info(f"Enhanced {len(enhanced_results)} VCP screener results with live data")
                return enhanced_results
                
            except Exception as e:
                logger.error(f"Error enhancing VCP screener results with live data: {e}")
                # Return original results with fallback change calculation
                for result in results:
                    if 'change' not in result:
                        result['change'] = result.get('change_pct', 0)
                    if 'current_price' not in result:
                        result['current_price'] = result.get('entry_price', 0)
                    if 'last_price' not in result:
                        result['last_price'] = result.get('entry_price', 0)
                return results

        else:
            # Preserving old logic for any other screeners
            data = ScreenerResult.fetch_by_screener(cur, screener_name)
            if not data:
                return []
            # Convert list of tuples to list of dicts for consistency
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in data]

    except Exception as e:
        logger.error(f"Error fetching data for screener '{screener_name}': {e}", exc_info=True)
        return []
    finally:
        if conn and cur:
            close_db_connection()
