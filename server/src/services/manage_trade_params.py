import datetime
import logging
from db import get_trade_db_connection, release_trade_db_connection
from .manage_risk_pool import update_risk_pool_on_parameter_change
from controllers import kite

logger = logging.getLogger(__name__)

def adjust_trade_parameters(symbol, new_stop_loss=None, new_target=None):
    conn, cur = get_trade_db_connection()
    try:
        cur.execute("""
            SELECT trade_id, stop_loss, target, entry_price, current_qty 
            FROM trades 
            WHERE stock_name = %s;
        """, (symbol,))
        trade = cur.fetchone()
        if not trade:
            logger.error(f"No active trade found for symbol: {symbol}")
            return {
                "status": "error",
                "message": f"No active trade found for {symbol}. Please open a position before adjusting parameters."
            }
        trade_id = trade['trade_id']
        current_stop_loss = float(trade['stop_loss'])
        current_target = float(trade['target'])
        entry_price = float(trade['entry_price'])
        qty = float(trade['current_qty'])
        stop_loss_msg = ""
        target_msg = ""
        if new_stop_loss is not None:
            try:
                new_stop_loss = float(new_stop_loss)
                if new_stop_loss <= 0:
                    raise ValueError("Stop loss must be a positive value.")
                if new_stop_loss != current_stop_loss:
                    logger.info(f"Updating stop loss for {symbol}: {current_stop_loss} -> {new_stop_loss}")
                    update_risk_pool_on_parameter_change(cur, current_stop_loss, new_stop_loss, entry_price, qty)
                    cur.execute("""
                        UPDATE trades
                        SET stop_loss = %s
                        WHERE trade_id = %s;
                    """, (new_stop_loss, trade_id))
                    logger.info(f"Stop loss updated for trade {trade_id}: New stop loss {new_stop_loss}")
                    stop_loss_msg = f"Stop loss changed from {current_stop_loss:.2f} to {new_stop_loss:.2f}."
            except ValueError as e:
                logger.error(f"Invalid stop loss value for {symbol}: {e}")
                return {
                    "status": "error",
                    "message": f"Invalid stop loss value for {symbol}: {str(e)}"
                }
        if new_target is not None:
            try:
                new_target = float(new_target)
                if new_target <= 0:
                    raise ValueError("Target must be a positive value.")
                if new_target != current_target:
                    logger.info(f"Updating target for {symbol}: {current_target} -> {new_target}")
                    cur.execute("""
                        UPDATE trades
                        SET target = %s
                        WHERE trade_id = %s;
                    """, (new_target, trade_id))
                    logger.info(f"Target updated for trade {trade_id}: New target {new_target}")
                    target_msg = f"Target changed from {current_target:.2f} to {new_target:.2f}."
            except ValueError as e:
                logger.error(f"Invalid target value for {symbol}: {e}")
                return {
                    "status": "error",
                    "message": f"Invalid target value for {symbol}: {str(e)}"
                }
        conn.commit()
        logger.info(f"Trade parameters updated successfully for {symbol}")
        return {
            "status": "success",
            "message": f"Trade parameters updated successfully for {symbol}. {stop_loss_msg} {target_msg}"
        }
    except Exception as e:
        conn.rollback()
        logger.error(f"Error adjusting trade parameters for {symbol}: {e}")
        return {
            "status": "error",
            "message": f"Error adjusting trade parameters for {symbol}: {str(e)}"
        }
    finally:
        release_trade_db_connection(conn, cur)
