# services/__init__.py

import logging
logger = logging.getLogger(__name__)

# (Your existing imports)
from .get_instruments_list import get_instrument_indices
from .get_equity_list import get_instrument_equity
from .get_historical_data import get_historical_data
from .get_ohlc import get_equity_ohlc_data_loop
from .place_buy import buy_order_execute
from .place_exit import sell_order_execute
from .place_adjust import adjust_order_execute
from .get_screener import run_vcp_screener, run_ipo_screener, load_precomputed_ohlc
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
from .auto_exit import process_live_auto_exit, toggle_auto_exit_flag
from .get_watchlist import add_stock_to_watchlist, get_watchlist_entries, search_equity

# IMPORTANT: import and re-export these so that "from services import filtered_tokens"
# or "from services import listen_for_data_changes" always references the SAME copy.
from .get_essential_tokens import listen_for_data_changes, filtered_tokens

__all__ = [
    "get_instrument_indices",
    "get_instrument_equity",
    "get_historical_data",
    "get_equity_ohlc_data_loop",
    "buy_order_execute",
    "sell_order_execute",
    "adjust_order_execute",
    "run_vcp_screener",
    "run_ipo_screener",
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
    "process_live_auto_exit",
    "toggle_auto_exit_flag",
    "add_stock_to_watchlist",
    "get_watchlist_entries",
    "search_equity",
    "listen_for_data_changes",
    "tokens_lock",
    "filtered_tokens",
]
