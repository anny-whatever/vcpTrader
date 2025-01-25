from models import RiskPool

def check_risk_pool_availability_for_buy(cur, entry_price, stop_loss_price, qty):
    """
    Check if sufficient risk is available in the risk pool for a new trade.

    Args:
        cur: Database cursor.
        entry_price (float): The current entry price (e.g., fetched from LTP).
        stop_loss_price (float): The calculated stop loss price.
        qty (int): The quantity of the trade.

    Returns:
        bool: True if sufficient risk is available, raises ValueError otherwise.
    """
    risk_for_trade = qty * abs(entry_price - stop_loss_price)
    risk_pool = RiskPool.fetch_risk_pool(cur)

    if risk_pool:
        available_risk = float(risk_pool['available_risk'])

        if available_risk < risk_for_trade:
            raise ValueError("Insufficient risk available for this trade.")

        print(f"Risk check passed: Available risk {available_risk}, Required risk {risk_for_trade}")
        return True
    else:
        raise ValueError("Risk pool is not initialized.")


def apply_risk_pool_update_on_buy(cur, average_price, stop_loss_price, qty):
    """
    Update the risk pool after a new trade is executed.

    Args:
        cur: Database cursor.
        average_price (float): The actual average price of the executed order.
        stop_loss_price (float): The calculated stop loss price.
        qty (int): The quantity of the trade.
    """
    risk_for_trade = qty * abs(average_price - stop_loss_price)
    risk_pool = RiskPool.fetch_risk_pool(cur)

    if risk_pool:
        available_risk = float(risk_pool['available_risk'])
        used_risk = float(risk_pool['used_risk'])

        try:
            # Update the risk pool
            RiskPool.update_used_risk(cur, used_risk + risk_for_trade)
            RiskPool.update_available_risk(cur, available_risk - risk_for_trade)
            print(f"Risk pool updated: Used risk increased by {risk_for_trade}, Available risk decreased by {risk_for_trade}")
        except Exception as e:
            print(f"Error updating risk pool: {e}")
    else:
        raise ValueError("Risk pool is not initialized.")


def update_risk_pool_on_increase(cur, initial_stop_loss, actual_price, qty):
    """
    Update the risk pool when the position size is increased.
    """
    additional_risk = qty * abs(actual_price - initial_stop_loss)
    risk_pool = RiskPool.fetch_risk_pool(cur)

    if risk_pool:
        available_risk = float(risk_pool['available_risk'])
        used_risk = float(risk_pool['used_risk'])

        # Check if sufficient risk is available
        if available_risk < additional_risk:
            raise ValueError("Insufficient risk available for this adjustment.")

        # Update the risk pool
        RiskPool.update_used_risk(cur, used_risk + additional_risk)
        RiskPool.update_available_risk(cur, available_risk - additional_risk)
    else:
        raise ValueError("Risk pool is not initialized.")

def update_risk_pool_on_decrease(cur, initial_stop_loss, entry_price, actual_price, qty):
    """
    Update the risk pool when the position size is decreased.

    Args:
        cur: Database cursor.
        initial_stop_loss (float): The original stop loss of the trade.
        entry_price (float): The entry price of the trade.
        actual_price (float): The price at which the position is partially exited.
        qty (float): The quantity being reduced from the position.
    """
    # Calculate the risk released based on the initial stop loss
    released_risk = qty * abs(actual_price - initial_stop_loss)

    # Fetch the risk pool
    risk_pool = RiskPool.fetch_risk_pool(cur)
    if not risk_pool:
        raise ValueError("Risk pool is not initialized.")

    available_risk = float(risk_pool['available_risk'])
    used_risk = float(risk_pool['used_risk'])

    # Determine profit or loss
    if actual_price > entry_price:
        # If in profit, calculate profit
        profit = (actual_price - entry_price) * qty
        new_available_risk = available_risk + released_risk + profit
    else:
        # If in loss, calculate loss
        loss = (entry_price - actual_price) * qty
        new_available_risk = available_risk + released_risk - (2 * loss)

    # Update the used risk
    new_used_risk = used_risk - released_risk

    # Ensure no negative values in the risk pool
    if new_available_risk < 0:
        raise ValueError("Available risk cannot be negative after update.")
    if new_used_risk < 0:
        raise ValueError("Used risk cannot be negative after update.")
    if new_available_risk >= 350000:
        new_available_risk = 350000
    if new_used_risk + new_available_risk <= 50000:
        new_available_risk = 50000 - new_used_risk
    # Commit the changes to the database
    RiskPool.update_available_risk(cur, new_available_risk)
    RiskPool.update_used_risk(cur, new_used_risk)

    print(f"Risk pool updated: Available risk={new_available_risk}, Used risk={new_used_risk}")


def update_risk_pool_on_exit(cur, initial_stop_loss, entry_price, actual_price, qty):
    """
    Update the risk pool when a position is exited.

    Args:
        cur: Database cursor.
        initial_stop_loss (float): The original stop loss of the trade.
        entry_price (float): The entry price of the trade.
        actual_price (float): The price at which the position is exited.
        qty (float): The quantity being exited.
    """
    # Calculate the risk released from the pool based on the initial stop loss
    released_risk = qty * abs(initial_stop_loss - entry_price)

    # Fetch the current risk pool
    risk_pool = RiskPool.fetch_risk_pool(cur)
    if not risk_pool:
        raise ValueError("Risk pool is not initialized.")

    available_risk = float(risk_pool['available_risk'])
    used_risk = float(risk_pool['used_risk'])

    # Determine if the exit is profitable
    if actual_price > entry_price:
        # If in profit, add profit to available risk
        profit = (actual_price - entry_price) * qty
        new_available_risk = available_risk + released_risk + profit
    else:
        # If in loss, deduct 2x the loss from available risk
        loss = (entry_price - actual_price) * qty
        new_available_risk = available_risk + released_risk - (2 * loss)

    # Update the used risk
    new_used_risk = used_risk - released_risk

    # Ensure no negative values in the risk pool
    if new_available_risk < 0:
        raise ValueError("Available risk cannot be negative after update.")
    if new_used_risk < 0:
        raise ValueError("Used risk cannot be negative after update.")
    if new_available_risk >= 350000:
        new_available_risk = 350000
    if new_used_risk + new_available_risk <= 50000:
        new_available_risk = 50000 - new_used_risk

    # Commit the changes to the database
    RiskPool.update_available_risk(cur, new_available_risk)
    RiskPool.update_used_risk(cur, new_used_risk)

    print(f"Risk pool updated: Available risk={new_available_risk}, Used risk={new_used_risk}")


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
    if new_stop_loss <= 0 or qty <= 0:
        raise ValueError("New stop loss and quantity must be positive values.")

    # Calculate current and new risks
    current_risk = qty * abs(entry_price - current_stop_loss)
    new_risk = qty * abs(entry_price - new_stop_loss)

    # Fetch the current risk pool
    risk_pool = RiskPool.fetch_risk_pool(cur)
    if not risk_pool:
        raise ValueError("Risk pool is not initialized.")
    
    available_risk = float(risk_pool['available_risk'])
    used_risk = float(risk_pool['used_risk'])

    try:
        if new_risk > current_risk:
            # Deduct the additional risk from available risk and add to used risk
            additional_risk = new_risk - current_risk
            if available_risk < additional_risk:
                raise ValueError("Insufficient available risk to adjust stop loss.")
            RiskPool.update_used_risk(cur, used_risk + additional_risk)
            RiskPool.update_available_risk(cur, available_risk - additional_risk)
            print(f"Risk pool updated: Additional risk of {additional_risk} applied.")
        elif new_risk < current_risk:
            # Release the reduced risk back to available risk and deduct from used risk
            released_risk = current_risk - new_risk
            RiskPool.update_used_risk(cur, used_risk - released_risk)
            RiskPool.update_available_risk(cur, available_risk + released_risk)
            print(f"Risk pool updated: Released risk of {released_risk}.")
        else:
            print("No change in risk. Stop loss adjustment does not alter the risk pool.")
    except Exception as e:
        print(f"Error updating risk pool: {e}")
        raise

    print(f"Risk pool updated: New risk based on stop loss {new_stop_loss}.")

