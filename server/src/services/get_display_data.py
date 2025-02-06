from models import RiskPool, SaveTradeDetails, SaveHistoricalTradeDetails
from db import get_db_connection, close_db_connection
import json
from datetime import datetime
from controllers import kite

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

