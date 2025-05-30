from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from db import get_db_connection, close_db_connection
from models.risk_scores import RiskScore
from services.risk_calculator import RiskCalculator, get_stock_risk_score, get_bulk_risk_scores

logger = logging.getLogger(__name__)
router = APIRouter()

# Thread pool for risk calculations
risk_calculation_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="risk_calc")

@router.get("/risk/single/{symbol}")
async def get_single_risk_score(symbol: str):
    """
    Get risk score for a single stock by symbol.
    """
    try:
        conn, cur = get_db_connection()
        
        # First check if we have a cached score
        query = """
            SELECT instrument_token FROM ohlc 
            WHERE symbol = %s AND interval = 'day' 
            ORDER BY date DESC LIMIT 1
        """
        cur.execute(query, (symbol,))
        result = cur.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
        
        instrument_token = result[0]
        
        # Check for cached risk score
        cached_score = RiskScore.get_by_instrument_token(cur, instrument_token)
        
        if cached_score:
            logger.info(f"Returning cached risk score for {symbol}")
            return cached_score
        
        # Calculate new risk score
        logger.info(f"Calculating new risk score for {symbol}")
        risk_result = get_stock_risk_score(symbol, instrument_token)
        
        # Save to database
        RiskScore.bulk_save_risk_scores(cur, [risk_result])
        conn.commit()
        
        return risk_result
        
    except Exception as e:
        logger.error(f"Error getting risk score for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        close_db_connection()

@router.get("/risk/bulk")
async def get_bulk_risk_scores_endpoint(
    symbols: Optional[str] = None,
    limit: Optional[int] = 100,
    force_recalculate: Optional[bool] = False
):
    """
    Get risk scores for multiple stocks.
    
    Args:
        symbols: Comma-separated list of symbols (optional)
        limit: Maximum number of results (default 100)
        force_recalculate: Whether to force recalculation (default False)
    """
    try:
        conn, cur = get_db_connection()
        
        symbols_list = None
        if symbols:
            symbols_list = [s.strip().upper() for s in symbols.split(',')]
        
        if not force_recalculate:
            # Try to get cached scores first
            if symbols_list:
                cached_scores = RiskScore.get_risk_scores_for_symbols(cur, symbols_list)
            else:
                cached_scores = RiskScore.get_all_risk_scores(cur, limit=limit)
            
            if cached_scores:
                logger.info(f"Returning {len(cached_scores)} cached risk scores")
                return cached_scores
        
        # Calculate new risk scores
        logger.info("Calculating new risk scores...")
        risk_results = get_bulk_risk_scores(symbols_list, limit)
        
        if risk_results:
            # Save to database
            RiskScore.bulk_save_risk_scores(cur, risk_results)
            conn.commit()
            logger.info(f"Saved {len(risk_results)} risk scores to database")
        
        return risk_results
        
    except Exception as e:
        logger.error(f"Error getting bulk risk scores: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        close_db_connection()

@router.get("/risk/ranking")
async def get_risk_ranking(
    limit: Optional[int] = 50,
    order_by: Optional[str] = "overall_risk_score"
):
    """
    Get stocks ranked by risk score.
    
    Args:
        limit: Maximum number of results (default 50)
        order_by: Field to order by (default 'overall_risk_score')
    """
    try:
        conn, cur = get_db_connection()
        
        # Validate order_by parameter
        valid_columns = [
            'overall_risk_score', 'volatility_score', 'atr_risk_score',
            'drawdown_risk_score', 'gap_risk_score', 'volume_consistency_score',
            'trend_stability_score', 'symbol'
        ]
        
        if order_by not in valid_columns:
            order_by = 'overall_risk_score'
        
        risk_scores = RiskScore.get_all_risk_scores(cur, limit=limit, order_by=order_by)
        
        return {
            'ranking': risk_scores,
            'count': len(risk_scores),
            'ordered_by': order_by
        }
        
    except Exception as e:
        logger.error(f"Error getting risk ranking: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        close_db_connection()

@router.post("/risk/calculate")
async def calculate_risk_scores(
    symbols: Optional[str] = None,
    limit: Optional[int] = 200
):
    """
    Calculate and store risk scores for stocks using thread pool.
    This runs asynchronously to avoid blocking other operations.
    
    Args:
        symbols: Comma-separated list of symbols (optional)
        limit: Maximum number of symbols to process (default 200)
    """
    try:
        symbols_list = None
        if symbols:
            symbols_list = [s.strip().upper() for s in symbols.split(',')]
        
        # Start calculation in thread pool
        loop = asyncio.get_event_loop()
        loop.run_in_executor(
            risk_calculation_executor,
            _calculate_and_store_risk_scores_sync,
            symbols_list,
            limit
        )
        
        return {
            "message": "Risk score calculation started in thread pool",
            "symbols": len(symbols_list) if symbols_list else "all",
            "limit": limit,
            "status": "processing"
        }
        
    except Exception as e:
        logger.error(f"Error starting risk calculation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/risk/cleanup")
async def cleanup_old_risk_scores(days_old: Optional[int] = 7):
    """
    Delete risk scores older than specified days.
    """
    try:
        conn, cur = get_db_connection()
        RiskScore.delete_old_scores(cur, days_old)
        conn.commit()
        
        return {"message": f"Deleted risk scores older than {days_old} days"}
        
    except Exception as e:
        logger.error(f"Error cleaning up risk scores: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        close_db_connection()

def _calculate_and_store_risk_scores_sync(symbols_list: Optional[List[str]], limit: int):
    """
    Synchronous function to calculate and store risk scores in thread pool.
    """
    try:
        logger.info(f"Starting thread pool risk calculation for {len(symbols_list) if symbols_list else 'all'} symbols")
        
        calculator = RiskCalculator()
        risk_results = calculator.calculate_bulk_risk_scores(symbols_list, limit)
        
        if risk_results:
            conn, cur = get_db_connection()
            try:
                RiskScore.bulk_save_risk_scores(cur, risk_results)
                conn.commit()
                logger.info(f"Thread pool: Saved {len(risk_results)} risk scores")
            finally:
                close_db_connection()
        
    except Exception as e:
        logger.error(f"Error in thread pool risk calculation: {e}")

# Keep the old background task method for backward compatibility
async def _calculate_and_store_risk_scores(symbols_list: Optional[List[str]], limit: int):
    """
    Background task to calculate and store risk scores.
    """
    try:
        logger.info(f"Starting background risk calculation for {len(symbols_list) if symbols_list else 'all'} symbols")
        
        calculator = RiskCalculator()
        risk_results = calculator.calculate_bulk_risk_scores(symbols_list, limit)
        
        if risk_results:
            conn, cur = get_db_connection()
            try:
                RiskScore.bulk_save_risk_scores(cur, risk_results)
                conn.commit()
                logger.info(f"Background task: Saved {len(risk_results)} risk scores")
            finally:
                close_db_connection()
        
    except Exception as e:
        logger.error(f"Error in background risk calculation: {e}")

@router.get("/risk/components/{symbol}")
async def get_risk_components(symbol: str):
    """
    Get detailed risk component breakdown for a symbol.
    """
    try:
        conn, cur = get_db_connection()
        
        # Get instrument token
        query = """
            SELECT instrument_token FROM ohlc 
            WHERE symbol = %s AND interval = 'day' 
            ORDER BY date DESC LIMIT 1
        """
        cur.execute(query, (symbol,))
        result = cur.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
        
        instrument_token = result[0]
        risk_score = RiskScore.get_by_instrument_token(cur, instrument_token)
        
        if not risk_score:
            # Calculate if not cached
            risk_score = get_stock_risk_score(symbol, instrument_token)
            RiskScore.bulk_save_risk_scores(cur, [risk_score])
            conn.commit()
        
        # Format detailed response
        return {
            'symbol': symbol,
            'overall_risk_score': risk_score['overall_risk_score'],
            'risk_level': _get_risk_level(risk_score['overall_risk_score']),
            'components': {
                'volatility': {
                    'score': risk_score.get('volatility_score', 5),
                    'weight': '30%',
                    'description': 'Price movement consistency'
                },
                'atr_risk': {
                    'score': risk_score.get('atr_risk_score', 5),
                    'weight': '20%',
                    'description': 'Average True Range relative to price'
                },
                'drawdown_risk': {
                    'score': risk_score.get('drawdown_risk_score', 5),
                    'weight': '20%',
                    'description': 'Maximum decline from peaks'
                },
                'gap_risk': {
                    'score': risk_score.get('gap_risk_score', 5),
                    'weight': '15%',
                    'description': 'Overnight/weekend price gaps'
                },
                'volume_consistency': {
                    'score': risk_score.get('volume_consistency_score', 5),
                    'weight': '10%',
                    'description': 'Trading volume stability'
                },
                'trend_stability': {
                    'score': risk_score.get('trend_stability_score', 5),
                    'weight': '5%',
                    'description': 'Directional consistency'
                }
            },
            'calculated_at': risk_score.get('calculated_at'),
            'data_points': risk_score.get('data_points', 0)
        }
        
    except Exception as e:
        logger.error(f"Error getting risk components for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        close_db_connection()

@router.get("/risk/simple/{symbol}")
async def get_simple_risk_score(symbol: str):
    """
    Get simple risk score for chart modal display.
    """
    try:
        conn, cur = get_db_connection()
        
        # Get instrument token
        query = """
            SELECT instrument_token FROM ohlc 
            WHERE symbol = %s AND interval = 'day' 
            ORDER BY date DESC LIMIT 1
        """
        cur.execute(query, (symbol,))
        result = cur.fetchone()
        
        if not result:
            return {
                'symbol': symbol,
                'overall_risk_score': None,
                'risk_level': 'Unknown',
                'error': 'Symbol not found'
            }
        
        instrument_token = result[0]
        risk_score = RiskScore.get_by_instrument_token(cur, instrument_token)
        
        if not risk_score:
            return {
                'symbol': symbol,
                'overall_risk_score': None,
                'risk_level': 'Not Calculated',
                'message': 'Risk score not yet calculated'
            }
        
        return {
            'symbol': symbol,
            'overall_risk_score': risk_score['overall_risk_score'],
            'risk_level': _get_risk_level(risk_score['overall_risk_score']),
            'calculated_at': risk_score.get('calculated_at')
        }
        
    except Exception as e:
        logger.error(f"Error getting simple risk score for {symbol}: {e}")
        return {
            'symbol': symbol,
            'overall_risk_score': None,
            'risk_level': 'Error',
            'error': str(e)
        }
    finally:
        close_db_connection()

def _get_risk_level(score: float) -> str:
    """Convert numeric risk score to descriptive level."""
    if score <= 2.0:
        return "Very Low"
    elif score <= 3.5:
        return "Low" 
    elif score <= 5.0:
        return "Medium"
    elif score <= 7.0:
        return "High"
    elif score <= 8.5:
        return "Very High"
    else:
        return "Extreme" 