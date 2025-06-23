from models import RiskPool
import logging

logger = logging.getLogger(__name__)

def check_risk_pool_availability_for_buy(cur, entry_price, stop_loss_price, qty):
    """
    Check if sufficient risk is available in the risk pool for a new trade.
    """
    risk_for_trade = qty * abs(entry_price - stop_loss_price)
    risk_pool = _fetch_risk_pool_for_update(cur)
    available_risk = risk_pool["available_risk"]
    if available_risk < risk_for_trade:
        raise ValueError(f"Insufficient risk available for this trade. Required: {risk_for_trade}, Available: {available_risk}")
    logger.info(f"Risk check passed: Available risk {available_risk}, Required risk {risk_for_trade}")
    return True

def apply_risk_pool_update_on_buy(cur, average_price, stop_loss_price, qty):
    """
    Apply risk pool updates on a buy transaction.
    """
    risk_for_trade = qty * abs(average_price - stop_loss_price)
    risk_pool = _fetch_risk_pool_for_update(cur)
    available_risk = risk_pool["available_risk"]
    used_risk = risk_pool["used_risk"]
    
    # Verify we have enough available risk
    if available_risk < risk_for_trade:
        raise ValueError(f"Insufficient available risk: Required {risk_for_trade}, Available {available_risk}")
    
    # Update the risk pools
    new_used_risk = used_risk + risk_for_trade
    new_available_risk = available_risk - risk_for_trade
    
    # Apply constraints
    if new_available_risk < 0:
        raise ValueError(f"Available risk would become negative ({new_available_risk})")
    
    # Enforce minimum combined risk
    if new_used_risk + new_available_risk < 100000:
        logger.warning(f"Combined risk would drop below 100000. Adjusting available risk.")
        new_available_risk = 100000 - new_used_risk
    
    try:
        RiskPool.update_used_risk(cur, new_used_risk)
        RiskPool.update_available_risk(cur, new_available_risk)
        logger.info(
            f"Risk pool updated on buy: Used risk increased to {new_used_risk}, "
            f"Available risk decreased to {new_available_risk}"
        )
    except Exception as e:
        logger.error(f"Error updating risk pool on buy: {e}")
        raise e

def update_risk_pool_on_increase(cur, initial_stop_loss, actual_price, qty):
    """
    When the risk increases (for example, due to adding to an existing position), 
    this function updates the risk pool by adding additional risk.
    """
    additional_risk = qty * abs(actual_price - initial_stop_loss)
    risk_pool = _fetch_risk_pool_for_update(cur)
    available_risk = risk_pool["available_risk"]
    used_risk = risk_pool["used_risk"]
    
    # Check if we have enough available risk
    if available_risk < additional_risk:
        raise ValueError(f"Insufficient available risk: Required {additional_risk}, Available {available_risk}")
    
    # Update risk pools
    new_used_risk = used_risk + additional_risk
    new_available_risk = available_risk - additional_risk
    
    # Validation
    if new_available_risk < 0:
        logger.warning(f"Available risk would become negative ({new_available_risk}). Capping at 0.")
        new_available_risk = 0
    
    # Enforce constraints:
    # 1. Maximum available risk cap
    new_available_risk = min(new_available_risk, 450000)
    
    # 2. Minimum combined risk floor
    if new_used_risk + new_available_risk < 100000:
        new_available_risk = 100000 - new_used_risk
        logger.info(f"Enforcing minimum combined risk of 100000. Adjusted available risk to {new_available_risk}.")

    RiskPool.update_used_risk(cur, new_used_risk)
    RiskPool.update_available_risk(cur, new_available_risk)
    logger.info(
        f"Risk pool updated on increase: Additional risk {additional_risk} applied. "
        f"New used risk: {new_used_risk}, New available risk: {new_available_risk}"
    )

def update_risk_pool_on_decrease(cur, initial_stop_loss, entry_price, actual_price, qty):
    """
    When the risk decreases (for example, due to a partial quantity decrement),
    update the risk pool by:
    1. First releasing the risk for the reduced portion of the position
    2. Then separately applying profit/loss adjustments for that portion
    
    Note: 'actual_price' is the price at which the quantity is decreased.
    """
    # Calculate the risk that was allocated for this portion of the trade
    released_risk = qty * abs(entry_price - initial_stop_loss)
    
    # Calculate profit or loss from the reduced portion
    if actual_price > entry_price:
        is_profit = True
        pnl_amount = (actual_price - entry_price) * qty
    else:
        is_profit = False
        pnl_amount = (entry_price - actual_price) * qty
    
    # Fetch current risk pool values
    risk_pool = _fetch_risk_pool_for_update(cur)
    available_risk = risk_pool["available_risk"]
    used_risk = risk_pool["used_risk"]
    
    # Step 1: Release the risk from used to available
    intermediate_available_risk = available_risk + released_risk
    intermediate_used_risk = used_risk - released_risk
    
    logger.info(
        f"Step 1 - Risk release: Released risk {released_risk} for qty={qty}. "
        f"Intermediate available risk: {intermediate_available_risk}, "
        f"Intermediate used risk: {intermediate_used_risk}"
    )
    
    # Step 2: Adjust available risk based on profit/loss
    if is_profit:
        final_available_risk = intermediate_available_risk + pnl_amount
        logger.info(f"Step 2 - Profit adjustment: Added profit {pnl_amount} to available risk.")
    else:
        final_available_risk = intermediate_available_risk - (2 * pnl_amount)
        logger.info(f"Step 2 - Loss adjustment: Subtracted 2x loss {2 * pnl_amount} from available risk.")
    
    final_used_risk = intermediate_used_risk
    
    # Validation checks
    if final_available_risk < 0:
        logger.warning(f"Available risk would become negative ({final_available_risk}). Capping at 0.")
        final_available_risk = 0
    
    if final_used_risk < 0:
        logger.warning(f"Used risk would become negative ({final_used_risk}). Capping at 0.")
        final_used_risk = 0
    
    # Apply constraints:
    # 1. Maximum available risk cap
    final_available_risk = min(final_available_risk, 450000)
    
    # 2. Minimum combined risk floor
    if final_used_risk + final_available_risk < 100000:
        final_available_risk = 100000 - final_used_risk
        logger.info(f"Enforcing minimum combined risk of 100000. Adjusted available risk to {final_available_risk}.")
    
    # Update the risk pool
    RiskPool.update_available_risk(cur, final_available_risk)
    RiskPool.update_used_risk(cur, final_used_risk)
    
    logger.info(
        f"Risk pool updated on decrease: Final available risk={final_available_risk}, "
        f"Final used risk={final_used_risk}"
    )

def update_risk_pool_on_exit(cur, initial_stop_loss, entry_price, actual_price, qty):
    """
    When a position is exited, update the risk pool by:
    1. First releasing the risk that was held for the entire position
    2. Then separately applying profit/loss adjustments
    """
    # Calculate the risk that was allocated for this trade
    released_risk = qty * abs(entry_price - initial_stop_loss)
    
    # Calculate profit or loss from the trade
    if actual_price > entry_price:
        is_profit = True
        pnl_amount = (actual_price - entry_price) * qty
    else:
        is_profit = False
        pnl_amount = (entry_price - actual_price) * qty
    
    # Fetch current risk pool values
    risk_pool = _fetch_risk_pool_for_update(cur)
    available_risk = risk_pool["available_risk"]
    used_risk = risk_pool["used_risk"]
    
    # Step 1: Release the risk from used to available
    intermediate_available_risk = available_risk + released_risk
    intermediate_used_risk = used_risk - released_risk
    
    logger.info(
        f"Step 1 - Risk release: Released risk {released_risk}. "
        f"Intermediate available risk: {intermediate_available_risk}, "
        f"Intermediate used risk: {intermediate_used_risk}"
    )
    
    # Step 2: Adjust available risk based on profit/loss
    if is_profit:
        final_available_risk = intermediate_available_risk + pnl_amount
        logger.info(f"Step 2 - Profit adjustment: Added profit {pnl_amount} to available risk.")
    else:
        final_available_risk = intermediate_available_risk - (2 * pnl_amount)
        logger.info(f"Step 2 - Loss adjustment: Subtracted 2x loss {2 * pnl_amount} from available risk.")
    
    final_used_risk = intermediate_used_risk
    
    # Validation checks
    if final_available_risk < 0:
        logger.warning(f"Available risk would become negative ({final_available_risk}). Capping at 0.")
        final_available_risk = 0
    
    if final_used_risk < 0:
        logger.warning(f"Used risk would become negative ({final_used_risk}). Capping at 0.")
        final_used_risk = 0
    
    # Apply constraints:
    # 1. Maximum available risk cap
    final_available_risk = min(final_available_risk, 450000)
    
    # 2. Minimum combined risk floor
    if final_used_risk + final_available_risk < 100000:
        final_available_risk = 100000 - final_used_risk
        logger.info(f"Enforcing minimum combined risk of 100000. Adjusted available risk to {final_available_risk}.")
    
    # Update the risk pool
    RiskPool.update_available_risk(cur, final_available_risk)
    RiskPool.update_used_risk(cur, final_used_risk)
    
    logger.info(
        f"Risk pool updated on exit: Final available risk={final_available_risk}, "
        f"Final used risk={final_used_risk}"
    )

def update_risk_pool_on_parameter_change(cur, current_stop_loss, new_stop_loss, entry_price, qty):
    """
    When stop-loss or target parameters change, update the risk pool to reflect
    the change in risk exposure.
    
    This function:
    1. Calculates the current and new risk amounts
    2. Determines the delta (increase or decrease)
    3. Updates the risk pool accordingly
    """
    current_risk = qty * abs(entry_price - current_stop_loss)
    new_risk = qty * abs(entry_price - new_stop_loss)
    risk_delta = new_risk - current_risk
    
    logger.info(
        f"Parameter change risk calculation: Current risk={current_risk}, "
        f"New risk={new_risk}, Delta={risk_delta}"
    )
    
    # Fetch current risk pool values
    risk_pool = _fetch_risk_pool_for_update(cur)
    available_risk = risk_pool["available_risk"]
    used_risk = risk_pool["used_risk"]
    
    if risk_delta > 0:
        # Risk is increasing, need to check availability
        if available_risk < risk_delta:
            raise ValueError(
                f"Insufficient available risk for parameter change. "
                f"Required: {risk_delta}, Available: {available_risk}"
            )
        
        new_used_risk = used_risk + risk_delta
        new_available_risk = available_risk - risk_delta
        logger.info(f"Risk increasing: Adding {risk_delta} to used risk")
        
    elif risk_delta < 0:
        # Risk is decreasing, release the risk
        risk_to_release = abs(risk_delta)
        new_used_risk = used_risk - risk_to_release
        new_available_risk = available_risk + risk_to_release
        logger.info(f"Risk decreasing: Releasing {risk_to_release} from used risk")
        
    else:
        # No change in risk
        logger.info("No change in risk exposure")
        return
    
    # Validation checks
    if new_available_risk < 0:
        logger.warning(f"Available risk would become negative ({new_available_risk}). Capping at 0.")
        new_available_risk = 0
    
    if new_used_risk < 0:
        logger.warning(f"Used risk would become negative ({new_used_risk}). Capping at 0.")
        new_used_risk = 0
    
    # Apply constraints:
    # 1. Maximum available risk cap
    new_available_risk = min(new_available_risk, 450000)
    
    # 2. Minimum combined risk floor
    if new_used_risk + new_available_risk < 100000:
        new_available_risk = 100000 - new_used_risk
        logger.info(f"Enforcing minimum combined risk of 100000. Adjusted available risk to {new_available_risk}.")
    
    # Update the risk pool
    RiskPool.update_used_risk(cur, new_used_risk)
    RiskPool.update_available_risk(cur, new_available_risk)
    
    logger.info(
        f"Risk pool updated on parameter change: Used risk={new_used_risk}, "
        f"Available risk={new_available_risk}"
    )

def _fetch_risk_pool_for_update(cur):
    """
    Helper function to fetch the current risk pool state.
    Returns a dictionary with 'available_risk' and 'used_risk' keys.
    """
    try:
        risk_pool_data = RiskPool.fetch_risk_pool(cur)
        if not risk_pool_data:
            logger.warning("No risk pool data found. Using default values.")
            return {"available_risk": 400000.0, "used_risk": 0.0}
        
        return {
            "available_risk": float(risk_pool_data[0]),
            "used_risk": float(risk_pool_data[1])
        }
    except Exception as e:
        logger.error(f"Error fetching risk pool data: {e}")
        raise e