from models import RiskPool, SaveTradeDetails, SaveHistoricalTradeDetails, SaveOHLC
from db import get_db_connection, close_db_connection
import json
from datetime import datetime
from controllers import kite
import pytz
from datetime import datetime, time


TIMEZONE = pytz.timezone("Asia/Kolkata")
MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 35)

def fetch_risk_pool_for_display():
    conn, cur = get_db_connection()
    try:
        risk_pool = RiskPool.fetch_risk_pool(cur)
        if risk_pool:
            return {
                "used_risk": float(risk_pool['used_risk']),
                "available_risk": float(risk_pool['available_risk'])
            }
        return None
    finally:
        close_db_connection()

def format_trade_record(trade):
    return {
        "stock_name": trade['stock_name'],
        "token": trade['token'],
        "entry_time": trade['entry_time'].isoformat(),
        "entry_price": float(trade['entry_price']),
        "stop_loss": float(trade['stop_loss']),
        "target": float(trade['target']),
        "initial_qty": float(trade['initial_qty']),
        "current_qty": float(trade['current_qty']),
        "booked_pnl": float(trade['booked_pnl'])
    }

def fetch_trade_details_for_display():
    conn, cur = get_db_connection()
    try:
        # Fetch existing trade details from database
        trade_details = SaveTradeDetails.fetch_all_trades(cur)
        if not trade_details:
            return []

        # Extract unique instrument tokens from all trades
        unique_tokens = list({trade['token'] for trade in trade_details})

        # Fetch live quotes from Kite API
        try:
            live_quotes = kite.quote(unique_tokens)  # Assuming 'kite' is properly imported
        except Exception as e:
            print(f"Error fetching live quotes: {e}")
            live_quotes = {}

        # Format trades with live data
        formatted_trades = []
        for trade in trade_details:
            # Format base trade data
            formatted = format_trade_record(trade)
            
            # Add live price data
            token_str = str(trade['token'])  # Kite API returns tokens as strings in quotes
            formatted['last_price'] = float(live_quotes.get(token_str, {}).get('last_price', 0))
            
            formatted_trades.append(formatted)

        return formatted_trades
    finally:
        close_db_connection()


def format_historical_trade_record(trade):
    return {
        "stock_name": trade['stock_name'],
        "entry_time": trade['entry_time'].isoformat(),
        "entry_price": float(trade['entry_price']),
        "exit_time": trade['exit_time'].isoformat() if trade['exit_time'] else None,
        "exit_price": float(trade['exit_price']),
        "final_pnl": float(trade['final_pnl']),
        "highest_qty": float(trade['highest_qty'])
    }

def fetch_historical_trade_details_for_display():
    conn, cur = get_db_connection()
    try:
        trade_details = SaveHistoricalTradeDetails.fetch_all_historical_trades(cur)
        return [format_historical_trade_record(trade) for trade in trade_details] if trade_details else []
    finally:
        close_db_connection()

def get_combined_ohlc(instrument_token, symbol):
    """
    Fetch historical OHLC data and combine with real-time data from Kite API
    Returns: List of OHLC records sorted by date (oldest first)
    """
    conn, cur = get_db_connection()
    combined_data = []
    
    try:
        # 1. Fetch historical data from database
        historical_data = SaveOHLC.fetch_by_instrument(cur, instrument_token)
        combined_data = [dict(record) for record in historical_data]

        # 2. Check if we need to add today's data
        now = datetime.now(TIMEZONE)
        today_date = now.date()
        
        if not historical_data:
            return combined_data
            
        # Get last historical date from DB
        last_historical_date = historical_data[-1]['date'].astimezone(TIMEZONE).date()
        
        if last_historical_date < today_date and MARKET_OPEN <= now.time() <= MARKET_CLOSE:
            # 3. Get live quote data from Kite
            try:
                quote = kite.quote(instrument_token)[str(instrument_token)]
                ohlc = quote.get('ohlc', {})
                
                if ohlc:
                    # 4. Create today's OHLC entry
                    today_open = ohlc['open'] if ohlc['open'] > 0 else historical_data[-1]['close']
                    today_entry = {
                        'instrument_token': instrument_token,
                        'symbol': symbol,
                        'interval': 'day',
                        'date': TIMEZONE.localize(datetime.combine(today_date, time(15, 30))),
                        'open': today_open,
                        'high': ohlc['high'],
                        'low': ohlc['low'],
                        'close': ohlc['close'],
                        'volume': quote.get('volume_today', 0)
                    }
                    
                    # 5. Append to combined data
                    combined_data.append(today_entry)
            except Exception as e:
                print(f"Error fetching live data for {symbol}: {e}")

        # Convert datetime objects to strings for JSON serialization
        formatted_data = []
        for record in combined_data:
            formatted = {**record}
            formatted['date'] = formatted['date'].isoformat()
            for key in ['open', 'high', 'low', 'close', 'volume']:
                formatted[key] = float(formatted[key])
            formatted_data.append(formatted)

        return formatted_data

    finally:
        close_db_connection()