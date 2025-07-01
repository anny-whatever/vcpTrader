# services/__init__.py

import logging
logger = logging.getLogger(__name__)

# (Your existing imports)
from .get_instruments_list import get_instrument_indices
from .get_equity_list import get_instrument_equity
from .get_historical_data import get_historical_data
# Removed get_equity_ohlc_data_loop import to avoid circular dependencies
# Import directly when needed: from services.get_ohlc import get_equity_ohlc_data_loop
# Keep these imports for backward compatibility but users should migrate to order_manager
from .place_buy import buy_order_execute
from .place_exit import sell_order_execute
from .place_adjust import adjust_order_execute
# Import the order_manager explicitly
from .order_manager import execute_buy, execute_sell, execute_adjust, get_order_status
from .get_screener import (
    run_vcp_screener,
    fetch_live_quotes,
    load_precomputed_ohlc,
    run_advanced_vcp_screener,
)
# Removed optimized_vcp_screener import to avoid circular dependencies
# Import directly when needed: from services.optimized_vcp_screener import run_optimized_vcp_screener_scheduled
from .manage_risk_pool import (
    update_risk_pool_on_increase,
    update_risk_pool_on_decrease,
    update_risk_pool_on_exit,
    apply_risk_pool_update_on_buy,
    check_risk_pool_availability_for_buy,
)
from .manage_trade_params import adjust_trade_parameters
from .get_display_data import (
    fetch_risk_pool_for_display,
    fetch_trade_details_for_display,
    fetch_historical_trade_details_for_display,
    get_combined_ohlc,
    get_all_alerts,
    get_latest_alert_messages,
    fetch_screener_data,
)
from .get_token_data import download_nse_csv
from .manage_alerts import (
    add_alert,
    remove_alert,
    create_and_send_alert_message,
    process_live_alerts,
)
from .send_telegram_alert import _send_telegram_in_thread
# Temporarily commented out to avoid circular imports for streaming VCP test
# from .auto_exit import process_live_auto_exit, toggle_auto_exit_flag
# Import directly when needed: from services.auto_exit import process_live_auto_exit, toggle_auto_exit_flag
from .get_watchlist import add_stock_to_watchlist, get_watchlist_entries, search_equity

# IMPORTANT: import and re-export these so that "from services import filtered_tokens"
# or "from services import listen_for_data_changes" always references the SAME copy.
from .get_essential_tokens import listen_for_data_changes, filtered_tokens
from .process_ticks import save_tradable_ticks, save_nontradable_ticks
from .resample_indices import calculate_ohlcv_15min, calculate_ohlcv_5min, calculate_ohlcv_1min
from .get_fno_list import get_instrument_fno
from .get_option_chain import generate_option_chain_nifty, filter_expiry_dates, generate_option_chain_bank_nifty, generate_option_chain_fin_nifty

# Re-export these new methods from SaveOHLC for broader use
from models.save_ohlc import SaveOHLC

__all__ = [
    "get_instrument_indices",
    "get_instrument_equity",
    "get_historical_data",
    # "get_equity_ohlc_data_loop",  # Removed to avoid circular imports
    # Old order functions
    "buy_order_execute",
    "sell_order_execute",
    "adjust_order_execute",
    # New order manager functions
    "execute_buy",
    "execute_sell",
    "execute_adjust",
    "get_order_status",
    "run_vcp_screener",
    "run_advanced_vcp_screener",
    "update_risk_pool_on_increase",
    "update_risk_pool_on_decrease",
    "update_risk_pool_on_exit",
    "apply_risk_pool_update_on_buy",
    "check_risk_pool_availability_for_buy",
    "adjust_trade_parameters",
    "fetch_risk_pool_for_display",
    "fetch_trade_details_for_display",
    "fetch_historical_trade_details_for_display",
    "get_combined_ohlc",
    "download_nse_csv",
    "add_alert",
    "remove_alert",
    "create_and_send_alert_message",
    "process_live_alerts",
    "get_all_alerts",
    "get_latest_alert_messages",
    # "process_live_auto_exit",      # Temporarily commented out to avoid circular imports
    # "toggle_auto_exit_flag",       # Temporarily commented out to avoid circular imports
    "add_stock_to_watchlist",
    "get_watchlist_entries",
    "search_equity",
    "listen_for_data_changes",
    "filtered_tokens",
    "save_tradable_ticks",
    "save_nontradable_ticks",
    "fetch_screener_data",
]
