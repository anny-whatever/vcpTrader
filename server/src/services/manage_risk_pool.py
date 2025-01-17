from models import RiskPool

def update_risk_pool_on_buy(cur, entry_price, stop_loss_price, qty):
    """
    Update the risk pool when a stock is bought.
    """
    risk_for_trade = qty * abs(entry_price - stop_loss_price)
    risk_pool = RiskPool.fetch_risk_pool(cur)

    if risk_pool:
        available_risk = risk_pool['available_risk']
        used_risk = risk_pool['used_risk']

        # Check if sufficient risk is available
        if available_risk < risk_for_trade:
            raise ValueError("Insufficient risk available for this trade.")

        # Update the risk pool
        RiskPool.update_used_risk(cur, used_risk + risk_for_trade)
        RiskPool.update_available_risk(cur, available_risk - risk_for_trade)
    else:
        raise ValueError("Risk pool is not initialized.")

def update_risk_pool_on_increase(cur, initial_stop_loss, actual_price, qty):
    """
    Update the risk pool when the position size is increased.
    """
    additional_risk = qty * abs(actual_price - initial_stop_loss)
    risk_pool = RiskPool.fetch_risk_pool(cur)

    if risk_pool:
        available_risk = risk_pool['available_risk']
        used_risk = risk_pool['used_risk']

        # Check if sufficient risk is available
        if available_risk < additional_risk:
            raise ValueError("Insufficient risk available for this adjustment.")

        # Update the risk pool
        RiskPool.update_used_risk(cur, used_risk + additional_risk)
        RiskPool.update_available_risk(cur, available_risk - additional_risk)
    else:
        raise ValueError("Risk pool is not initialized.")

def update_risk_pool_on_decrease(cur, initial_stop_loss, actual_price, qty, is_profit):
    """
    Update the risk pool when the position size is decreased.
    """
    released_risk = qty * abs(actual_price - initial_stop_loss)
    risk_pool = RiskPool.fetch_risk_pool(cur)

    if risk_pool:
        available_risk = risk_pool['available_risk']
        used_risk = risk_pool['used_risk']

        if is_profit:
            # Add profit to available risk
            profit = abs(actual_price - initial_stop_loss) * qty
            RiskPool.update_available_risk(cur, available_risk + released_risk + profit)
        else:
            # Deduct 2x the loss from available risk
            loss = abs(initial_stop_loss - actual_price) * qty
            RiskPool.update_available_risk(cur, available_risk + released_risk - (2 * loss))

        # Update the used risk
        RiskPool.update_used_risk(cur, used_risk - released_risk)
    else:
        raise ValueError("Risk pool is not initialized.")

def update_risk_pool_on_exit(cur, initial_stop_loss, actual_price, qty, is_profit):
    """
    Update the risk pool when a position is exited.
    """
    released_risk = qty * abs(actual_price - initial_stop_loss)
    risk_pool = RiskPool.fetch_risk_pool(cur)

    if risk_pool:
        available_risk = risk_pool['available_risk']
        used_risk = risk_pool['used_risk']

        if is_profit:
            # Add profit to available risk
            profit = abs(actual_price - initial_stop_loss) * qty
            RiskPool.update_available_risk(cur, available_risk + released_risk + profit)
        else:
            # Deduct 2x the loss from available risk
            loss = abs(initial_stop_loss - actual_price) * qty
            RiskPool.update_available_risk(cur, available_risk + released_risk - (2 * loss))

        # Update the used risk
        RiskPool.update_used_risk(cur, used_risk - released_risk)
    else:
        raise ValueError("Risk pool is not initialized.")

def update_risk_pool_on_parameter_change(cur, current_stop_loss, new_stop_loss, entry_price, qty):
    """
    Update the risk pool when the stop loss or target changes.
    
    Args:
        cur: Database cursor.
        current_stop_loss (float): The current stop loss.
        new_stop_loss (float): The new stop loss to be set.
        entry_price (float): The entry price of the trade.
        qty (float): The quantity of the trade.
    """
    # Calculate current and new risks
    current_risk = qty * abs(entry_price - current_stop_loss)
    new_risk = qty * abs(entry_price - new_stop_loss)

    # Fetch the current risk pool
    risk_pool = RiskPool.fetch_risk_pool(cur)
    if not risk_pool:
        raise ValueError("Risk pool is not initialized.")
    
    available_risk = risk_pool['available_risk']
    used_risk = risk_pool['used_risk']

    if new_risk > current_risk:
        # Deduct the additional risk from available risk and add to used risk
        additional_risk = new_risk - current_risk
        if available_risk < additional_risk:
            raise ValueError("Insufficient available risk to adjust stop loss.")
        RiskPool.update_used_risk(cur, used_risk + additional_risk)
        RiskPool.update_available_risk(cur, available_risk - additional_risk)
    elif new_risk < current_risk:
        # Release the reduced risk back to available risk and deduct from used risk
        released_risk = current_risk - new_risk
        RiskPool.update_used_risk(cur, used_risk - released_risk)
        RiskPool.update_available_risk(cur, available_risk + released_risk)

    print(f"Risk pool updated: New risk set based on stop loss {new_stop_loss}.")
