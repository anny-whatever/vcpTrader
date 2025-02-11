from models import RiskPool
import logging

logger = logging.getLogger(__name__)

def check_risk_pool_availability_for_buy(cur, entry_price, stop_loss_price, qty):
    """
    Check if sufficient risk is available in the risk pool for a new trade.
    """
    risk_for_trade = qty * abs(entry_price - stop_loss_price)
    risk_pool = RiskPool.fetch_risk_pool(cur)
    if risk_pool:
        available_risk = float(risk_pool['available_risk'])
        if available_risk < risk_for_trade:
            raise ValueError("Insufficient risk available for this trade.")
        logger.info(f"Risk check passed: Available risk {available_risk}, Required risk {risk_for_trade}")
        return True
    else:
        raise ValueError("Risk pool is not initialized.")

def apply_risk_pool_update_on_buy(cur, average_price, stop_loss_price, qty):
    """
    Apply risk pool updates on a buy transaction.
    """
    risk_for_trade = qty * abs(average_price - stop_loss_price)
    risk_pool = RiskPool.fetch_risk_pool(cur)
    if risk_pool:
        available_risk = float(risk_pool['available_risk'])
        used_risk = float(risk_pool['used_risk'])
        try:
            RiskPool.update_used_risk(cur, used_risk + risk_for_trade)
            RiskPool.update_available_risk(cur, available_risk - risk_for_trade)
            logger.info(f"Risk pool updated on buy: Used risk increased and Available risk decreased by {risk_for_trade}")
        except Exception as e:
            logger.error(f"Error updating risk pool on buy: {e}")
            raise e
    else:
        raise ValueError("Risk pool is not initialized.")

def update_risk_pool_on_increase(cur, initial_stop_loss, actual_price, qty):
    """
    When the risk increases (for example, due to an adverse price movement), 
    this function updates the risk pool by adding additional risk.
    """
    additional_risk = qty * abs(actual_price - initial_stop_loss)
    risk_pool = RiskPool.fetch_risk_pool(cur)
    if risk_pool:
        available_risk = float(risk_pool['available_risk'])
        used_risk = float(risk_pool['used_risk'])
        if available_risk < additional_risk:
            raise ValueError("Insufficient available risk for this adjustment.")
        new_used_risk = used_risk + additional_risk
        new_available_risk = available_risk - additional_risk

        # Enforce constraints:
        new_available_risk = min(new_available_risk, 350000)
        if new_used_risk + new_available_risk <= 50000:
            new_available_risk = 50000 - new_used_risk

        RiskPool.update_used_risk(cur, new_used_risk)
        RiskPool.update_available_risk(cur, new_available_risk)
        logger.info(
            f"Risk pool updated on increase: Additional risk {additional_risk} applied. "
            f"New used risk: {new_used_risk}, New available risk: {new_available_risk}"
        )
    else:
        raise ValueError("Risk pool is not initialized.")

def update_risk_pool_on_decrease(cur, initial_stop_loss, entry_price, actual_price, qty):
    """
    When the risk decreases (for example, due to a partial quantity decrement),
    update the risk pool by releasing some risk and accounting for profit/loss.
    
    Note: 'actual_price' is the price at which the quantity is decreased.
    """
    released_risk = qty * abs(actual_price - initial_stop_loss)
    risk_pool = RiskPool.fetch_risk_pool(cur)
    if not risk_pool:
        raise ValueError("Risk pool is not initialized.")

    available_risk = float(risk_pool['available_risk'])
    used_risk = float(risk_pool['used_risk'])

    # Adjust available risk based on profit or loss from the trade.
    if actual_price > entry_price:
        profit = (actual_price - entry_price) * qty
        new_available_risk = available_risk + released_risk + profit
    else:
        loss = (entry_price - actual_price) * qty
        new_available_risk = available_risk + released_risk - (2 * loss)
    new_used_risk = used_risk - released_risk

    if new_available_risk < 0:
        raise ValueError("Available risk cannot be negative after update.")
    if new_used_risk < 0:
        raise ValueError("Used risk cannot be negative after update.")

    # Enforce maximum cap and minimum combined risk.
    new_available_risk = min(new_available_risk, 350000)
    if new_used_risk + new_available_risk <= 50000:
        new_available_risk = 50000 - new_used_risk

    RiskPool.update_available_risk(cur, new_available_risk)
    RiskPool.update_used_risk(cur, new_used_risk)
    logger.info(
        f"Risk pool updated on decrease: New available risk={new_available_risk}, New used risk={new_used_risk}"
    )

def update_risk_pool_on_exit(cur, initial_stop_loss, entry_price, actual_price, qty):
    """
    When a position is exited, update the risk pool by releasing the risk that was held
    for the entire position. This function applies the same constraint logic as the decrease function.
    """
    released_risk = qty * abs(initial_stop_loss - entry_price)
    risk_pool = RiskPool.fetch_risk_pool(cur)
    if not risk_pool:
        raise ValueError("Risk pool is not initialized.")

    available_risk = float(risk_pool['available_risk'])
    used_risk = float(risk_pool['used_risk'])

    # Calculate new available risk considering profit or loss on the exit.
    if actual_price > entry_price:
        profit = (actual_price - entry_price) * qty
        new_available_risk = available_risk + released_risk + profit
    else:
        loss = (entry_price - actual_price) * qty
        new_available_risk = available_risk + released_risk - (2 * loss)
    new_used_risk = used_risk - released_risk

    if new_available_risk < 0:
        raise ValueError("Available risk cannot be negative after update.")
    if new_used_risk < 0:
        raise ValueError("Used risk cannot be negative after update.")

    # Enforce the same constraints:
    new_available_risk = min(new_available_risk, 350000)
    if new_used_risk + new_available_risk <= 50000:
        new_available_risk = 50000 - new_used_risk

    RiskPool.update_available_risk(cur, new_available_risk)
    RiskPool.update_used_risk(cur, new_used_risk)
    logger.info(
        f"Risk pool updated on exit: New available risk={new_available_risk}, New used risk={new_used_risk}"
    )

def update_risk_pool_on_parameter_change(cur, current_stop_loss, new_stop_loss, entry_price, qty):
    """
    When the stop-loss parameter is changed (adjusted tighter or looser), update the risk pool 
    based on the difference between the current and new stop loss values.
    """
    if new_stop_loss <= 0 or qty <= 0:
        raise ValueError("New stop loss and quantity must be positive values.")
    if current_stop_loss >= entry_price:
        current_risk = 0
    else:
        current_risk = qty * abs(entry_price - current_stop_loss)
    if new_stop_loss >= entry_price:
        new_risk = 0
    else:
        new_risk = qty * abs(entry_price - new_stop_loss)
    risk_pool = RiskPool.fetch_risk_pool(cur)
    if not risk_pool:
        raise ValueError("Risk pool is not initialized.")
    available_risk = float(risk_pool['available_risk'])
    used_risk = float(risk_pool['used_risk'])
    try:
        if new_risk > current_risk:
            additional_risk = new_risk - current_risk
            if available_risk < additional_risk:
                raise ValueError("Insufficient available risk to adjust stop loss.")
            new_used_risk = used_risk + additional_risk
            new_available_risk = available_risk - additional_risk

            new_available_risk = min(new_available_risk, 350000)
            if new_used_risk + new_available_risk <= 50000:
                new_available_risk = 50000 - new_used_risk

            RiskPool.update_used_risk(cur, new_used_risk)
            RiskPool.update_available_risk(cur, new_available_risk)
            logger.info(f"Risk pool updated on parameter change: Additional risk {additional_risk} applied.")
        elif new_risk < current_risk:
            released_risk = current_risk - new_risk
            new_used_risk = used_risk - released_risk
            new_available_risk = available_risk + released_risk

            new_available_risk = min(new_available_risk, 350000)
            if new_used_risk + new_available_risk <= 50000:
                new_available_risk = 50000 - new_used_risk

            RiskPool.update_used_risk(cur, new_used_risk)
            RiskPool.update_available_risk(cur, new_available_risk)
            logger.info(f"Risk pool updated on parameter change: Released risk {released_risk}.")
        else:
            logger.info("No change in risk. Stop loss adjustment does not alter the risk pool.")
    except Exception as e:
        logger.error(f"Error updating risk pool on parameter change: {e}")
        raise e
    logger.info(f"Risk pool updated: New risk based on stop loss {new_stop_loss}.")
