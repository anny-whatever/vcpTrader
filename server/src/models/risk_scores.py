import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class RiskScore:
    """
    Model for storing and retrieving stock risk scores.
    """
    
    def __init__(
        self,
        instrument_token,
        symbol,
        overall_risk_score,
        volatility_score=5,
        atr_risk_score=5,
        drawdown_risk_score=5,
        gap_risk_score=5,
        volume_consistency_score=5,
        trend_stability_score=5,
        data_points=0,
        calculated_at=None
    ):
        self.instrument_token = instrument_token
        self.symbol = symbol
        self.overall_risk_score = overall_risk_score
        self.volatility_score = volatility_score
        self.atr_risk_score = atr_risk_score
        self.drawdown_risk_score = drawdown_risk_score
        self.gap_risk_score = gap_risk_score
        self.volume_consistency_score = volume_consistency_score
        self.trend_stability_score = trend_stability_score
        self.data_points = data_points
        self.calculated_at = calculated_at if calculated_at else datetime.now()

    def save(self, cur):
        """
        Save risk score to database.
        """
        upsert_query = """
            INSERT INTO risk_scores (
                instrument_token,
                symbol,
                overall_risk_score,
                volatility_score,
                atr_risk_score,
                drawdown_risk_score,
                gap_risk_score,
                volume_consistency_score,
                trend_stability_score,
                data_points,
                calculated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (instrument_token)
            DO UPDATE SET
                symbol = EXCLUDED.symbol,
                overall_risk_score = EXCLUDED.overall_risk_score,
                volatility_score = EXCLUDED.volatility_score,
                atr_risk_score = EXCLUDED.atr_risk_score,
                drawdown_risk_score = EXCLUDED.drawdown_risk_score,
                gap_risk_score = EXCLUDED.gap_risk_score,
                volume_consistency_score = EXCLUDED.volume_consistency_score,
                trend_stability_score = EXCLUDED.trend_stability_score,
                data_points = EXCLUDED.data_points,
                calculated_at = EXCLUDED.calculated_at;
        """
        try:
            cur.execute(upsert_query, (
                self.instrument_token,
                self.symbol,
                self.overall_risk_score,
                self.volatility_score,
                self.atr_risk_score,
                self.drawdown_risk_score,
                self.gap_risk_score,
                self.volume_consistency_score,
                self.trend_stability_score,
                self.data_points,
                self.calculated_at
            ))
            logger.info(f"Risk score saved for {self.symbol}: {self.overall_risk_score}")
        except Exception as e:
            logger.error(f"Error saving risk score for {self.symbol}: {e}")
            raise e

    @classmethod
    def get_by_instrument_token(cls, cur, instrument_token):
        """
        Get risk score by instrument token.
        """
        query = """
            SELECT 
                instrument_token,
                symbol,
                overall_risk_score,
                volatility_score,
                atr_risk_score,
                drawdown_risk_score,
                gap_risk_score,
                volume_consistency_score,
                trend_stability_score,
                data_points,
                calculated_at
            FROM risk_scores
            WHERE instrument_token = %s;
        """
        try:
            cur.execute(query, (instrument_token,))
            result = cur.fetchone()
            if result:
                return {
                    'instrument_token': result[0],
                    'symbol': result[1],
                    'overall_risk_score': float(result[2]),
                    'volatility_score': int(result[3]),
                    'atr_risk_score': int(result[4]),
                    'drawdown_risk_score': int(result[5]),
                    'gap_risk_score': int(result[6]),
                    'volume_consistency_score': int(result[7]),
                    'trend_stability_score': int(result[8]),
                    'data_points': int(result[9]),
                    'calculated_at': result[10].isoformat() if result[10] else None
                }
            return None
        except Exception as e:
            logger.error(f"Error fetching risk score for token {instrument_token}: {e}")
            return None

    @classmethod
    def get_all_risk_scores(cls, cur, limit=None, order_by='overall_risk_score'):
        """
        Get all risk scores, optionally limited and ordered.
        """
        query = f"""
            SELECT 
                instrument_token,
                symbol,
                overall_risk_score,
                volatility_score,
                atr_risk_score,
                drawdown_risk_score,
                gap_risk_score,
                volume_consistency_score,
                trend_stability_score,
                data_points,
                calculated_at
            FROM risk_scores
            ORDER BY {order_by} ASC
        """
        if limit:
            query += f" LIMIT {limit}"
        
        try:
            cur.execute(query)
            results = cur.fetchall()
            risk_scores = []
            for result in results:
                risk_scores.append({
                    'instrument_token': result[0],
                    'symbol': result[1],
                    'overall_risk_score': float(result[2]),
                    'volatility_score': int(result[3]),
                    'atr_risk_score': int(result[4]),
                    'drawdown_risk_score': int(result[5]),
                    'gap_risk_score': int(result[6]),
                    'volume_consistency_score': int(result[7]),
                    'trend_stability_score': int(result[8]),
                    'data_points': int(result[9]),
                    'calculated_at': result[10].isoformat() if result[10] else None
                })
            return risk_scores
        except Exception as e:
            logger.error(f"Error fetching all risk scores: {e}")
            return []

    @classmethod
    def get_risk_scores_for_symbols(cls, cur, symbols_list):
        """
        Get risk scores for specific symbols.
        """
        if not symbols_list:
            return []
            
        placeholders = ','.join(['%s'] * len(symbols_list))
        query = f"""
            SELECT 
                instrument_token,
                symbol,
                overall_risk_score,
                volatility_score,
                atr_risk_score,
                drawdown_risk_score,
                gap_risk_score,
                volume_consistency_score,
                trend_stability_score,
                data_points,
                calculated_at
            FROM risk_scores
            WHERE symbol IN ({placeholders})
            ORDER BY overall_risk_score ASC;
        """
        
        try:
            cur.execute(query, symbols_list)
            results = cur.fetchall()
            risk_scores = []
            for result in results:
                risk_scores.append({
                    'instrument_token': result[0],
                    'symbol': result[1],
                    'overall_risk_score': float(result[2]),
                    'volatility_score': int(result[3]),
                    'atr_risk_score': int(result[4]),
                    'drawdown_risk_score': int(result[5]),
                    'gap_risk_score': int(result[6]),
                    'volume_consistency_score': int(result[7]),
                    'trend_stability_score': int(result[8]),
                    'data_points': int(result[9]),
                    'calculated_at': result[10].isoformat() if result[10] else None
                })
            return risk_scores
        except Exception as e:
            logger.error(f"Error fetching risk scores for symbols: {e}")
            return []

    @classmethod
    def delete_old_scores(cls, cur, days_old=7):
        """
        Delete risk scores older than specified days.
        """
        query = """
            DELETE FROM risk_scores
            WHERE calculated_at < NOW() - INTERVAL '%s days';
        """
        try:
            cur.execute(query, (days_old,))
            logger.info(f"Deleted risk scores older than {days_old} days")
        except Exception as e:
            logger.error(f"Error deleting old risk scores: {e}")
            raise e

    @classmethod
    def bulk_save_risk_scores(cls, cur, risk_scores_list):
        """
        Save multiple risk scores efficiently.
        """
        if not risk_scores_list:
            return
            
        upsert_query = """
            INSERT INTO risk_scores (
                instrument_token,
                symbol,
                overall_risk_score,
                volatility_score,
                atr_risk_score,
                drawdown_risk_score,
                gap_risk_score,
                volume_consistency_score,
                trend_stability_score,
                data_points,
                calculated_at
            )
            VALUES %s
            ON CONFLICT (instrument_token)
            DO UPDATE SET
                symbol = EXCLUDED.symbol,
                overall_risk_score = EXCLUDED.overall_risk_score,
                volatility_score = EXCLUDED.volatility_score,
                atr_risk_score = EXCLUDED.atr_risk_score,
                drawdown_risk_score = EXCLUDED.drawdown_risk_score,
                gap_risk_score = EXCLUDED.gap_risk_score,
                volume_consistency_score = EXCLUDED.volume_consistency_score,
                trend_stability_score = EXCLUDED.trend_stability_score,
                data_points = EXCLUDED.data_points,
                calculated_at = EXCLUDED.calculated_at;
        """
        try:
            # Prepare data for bulk insert
            values_list = []
            for score in risk_scores_list:
                values_list.append((
                    score.get('instrument_token'),
                    score.get('symbol'),
                    score.get('overall_risk_score'),
                    score.get('risk_components', {}).get('volatility', 5),
                    score.get('risk_components', {}).get('atr_risk', 5),
                    score.get('risk_components', {}).get('drawdown_risk', 5),
                    score.get('risk_components', {}).get('gap_risk', 5),
                    score.get('risk_components', {}).get('volume_consistency', 5),
                    score.get('risk_components', {}).get('trend_stability', 5),
                    score.get('data_points', 0),
                    datetime.now()
                ))
            
            # Use psycopg2's execute_values for efficient bulk insert
            from psycopg2.extras import execute_values
            execute_values(cur, upsert_query, values_list)
            logger.info(f"Bulk saved {len(risk_scores_list)} risk scores")
            
        except Exception as e:
            logger.error(f"Error in bulk save risk scores: {e}")
            raise e 