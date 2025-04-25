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
            raise ValueError(f"Insufficient risk available for this trade. Required: {risk_for_trade}, Available: {available_risk}")
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
    else:
        raise ValueError("Risk pool is not initialized.")

def update_risk_pool_on_increase(cur, initial_stop_loss, actual_price, qty):
    """
    When the risk increases (for example, due to adding to an existing position), 
    this function updates the risk pool by adding additional risk.
    """
    additional_risk = qty * abs(actual_price - initial_stop_loss)
    risk_pool = RiskPool.fetch_risk_pool(cur)
    if risk_pool:
        available_risk = float(risk_pool['available_risk'])
        used_risk = float(risk_pool['used_risk'])
        
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
    else:
        raise ValueError("Risk pool is not initialized.")

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
    risk_pool = RiskPool.fetch_risk_pool(cur)
    if not risk_pool:
        raise ValueError("Risk pool is not initialized.")
    
    available_risk = float(risk_pool['available_risk'])
    used_risk = float(risk_pool['used_risk'])
    
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
    risk_pool = RiskPool.fetch_risk_pool(cur)
    if not risk_pool:
        raise ValueError("Risk pool is not initialized.")
    
    available_risk = float(risk_pool['available_risk'])
    used_risk = float(risk_pool['used_risk'])
    
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
    When the stop-loss parameter is changed (adjusted tighter or looser), update the risk pool 
    based on the difference between the current and new stop loss values.
    """
    if new_stop_loss <= 0 or qty <= 0:
        raise ValueError("New stop loss and quantity must be positive values.")
    
    # Calculate current and new risk
    if current_stop_loss >= entry_price:
        current_risk = 0
    else:
        current_risk = qty * abs(entry_price - current_stop_loss)
    
    if new_stop_loss >= entry_price:
        new_risk = 0
    else:
        new_risk = qty * abs(entry_price - new_stop_loss)
    
    # Fetch risk pool data
    risk_pool = RiskPool.fetch_risk_pool(cur)
    if not risk_pool:
        raise ValueError("Risk pool is not initialized.")
    
    available_risk = float(risk_pool['available_risk'])
    used_risk = float(risk_pool['used_risk'])
    
    try:
        # Case 1: Risk is increasing (stop loss is being loosened)
        if new_risk > current_risk:
            additional_risk = new_risk - current_risk
            
            # Check if we have enough available risk
            if available_risk < additional_risk:
                raise ValueError(f"Insufficient available risk: Required {additional_risk}, Available {available_risk}")
            
            # Calculate new values
            new_used_risk = used_risk + additional_risk
            new_available_risk = available_risk - additional_risk
            
            logger.info(
                f"Stop loss adjusted looser: Additional risk {additional_risk}. "
                f"New used risk: {new_used_risk}, New available risk: {new_available_risk}"
            )
            
        # Case 2: Risk is decreasing (stop loss is being tightened)
        elif new_risk < current_risk:
            released_risk = current_risk - new_risk
            
            # Calculate new values
            new_used_risk = used_risk - released_risk
            new_available_risk = available_risk + released_risk
            
            logger.info(
                f"Stop loss adjusted tighter: Released risk {released_risk}. "
                f"New used risk: {new_used_risk}, New available risk: {new_available_risk}"
            )
            
        # Case 3: No change in risk
        else:
            logger.info("No change in risk. Stop loss adjustment does not alter the risk pool.")
            return
        
        # Validation
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
        
    except Exception as e:
        logger.error(f"Error updating risk pool on parameter change: {e}")
        raise e
    
    logger.info(f"Risk pool updated: New risk based on stop loss {new_stop_loss}.")