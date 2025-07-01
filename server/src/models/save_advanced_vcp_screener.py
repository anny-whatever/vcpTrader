import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class AdvancedVcpResult:
    """
    Model for interacting with the advanced_vcp_results table.
    Each record represents a stock that passed the advanced VCP screener.
    """

    @staticmethod
    def _clean_value(value, default=0.0):
        """Handle potential NaN or infinity values from pandas/numpy."""
        if value is None:
            return value
        import numpy as np
        # Convert numpy scalar types (including numpy.bool_) to native Python types
        if isinstance(value, np.generic):
            return value.item()
        # Handle NaN and infinity for numeric types
        if isinstance(value, (float, int)):
            if np.isnan(value) or np.isinf(value):
                return default
        return value

    @classmethod
    def batch_save(cls, cur, results: list[dict]):
        """
        Save multiple advanced VCP screener results in a single transaction.

        Args:
            cur: Database cursor.
            results: A list of dictionaries, where each dictionary contains
                     the metrics for a single stock breakout.
        """
        if not results:
            logger.info("No advanced VCP results to save.")
            return

        # Check if cursor is valid before proceeding
        if cur.closed:
            logger.error("Cursor is closed - cannot save advanced VCP results")
            raise Exception("Database cursor is closed")

        insert_query = """
            INSERT INTO advanced_vcp_results (
                instrument_token, symbol, scan_date, quality_score, pattern_duration_days,
                pattern_start_date, pattern_end_date, pattern_high, pattern_low,
                num_contractions, compression_ratio, breakout_date, breakout_price,
                breakout_high, breakout_volume, breakout_strength, volume_surge_ratio,
                sma_50, sma_150, sma_200, atr, entry_price, suggested_stop_loss,
                suggested_take_profit, risk_reward_ratio, duration_score, contraction_score,
                compression_score, volume_score, prior_uptrend_gain, price_breakout,
                volume_surge, green_breakout_candle, above_sma50, above_sma100,
                change_pct, additional_metrics, run_time, created_at
            ) VALUES (
                %(instrument_token)s, %(symbol)s, %(scan_date)s, %(quality_score)s, %(pattern_duration_days)s,
                %(pattern_start_date)s, %(pattern_end_date)s, %(pattern_high)s, %(pattern_low)s,
                %(num_contractions)s, %(compression_ratio)s, %(breakout_date)s, %(breakout_price)s,
                %(breakout_high)s, %(breakout_volume)s, %(breakout_strength)s, %(volume_surge_ratio)s,
                %(sma_50)s, %(sma_150)s, %(sma_200)s, %(atr)s, %(entry_price)s, %(suggested_stop_loss)s,
                %(suggested_take_profit)s, %(risk_reward_ratio)s, %(duration_score)s, %(contraction_score)s,
                %(compression_score)s, %(volume_score)s, %(prior_uptrend_gain)s, %(price_breakout)s,
                %(volume_surge)s, %(green_breakout_candle)s, %(above_sma50)s, %(above_sma100)s,
                %(change_pct)s, %(additional_metrics)s, %(run_time)s, %(created_at)s
            );
        """
        
        records_to_insert = []
        now = datetime.now()

        for res in results:
            # Prepare a dictionary that matches the table columns
            # This requires careful mapping from the screener output to the DDL.
            record = {
                'instrument_token': res.get('instrument_token'),
                'symbol': res.get('symbol'),
                'scan_date': res.get('scan_date'),
                'quality_score': res.get('quality_score'),
                'pattern_duration_days': res.get('pattern_duration_days'),
                'pattern_start_date': res.get('pattern_start_date'),
                'pattern_end_date': res.get('pattern_end_date'),
                'pattern_high': cls._clean_value(res.get('pattern_high')),
                'pattern_low': cls._clean_value(res.get('pattern_low')),
                'num_contractions': res.get('num_contractions'),
                'compression_ratio': cls._clean_value(res.get('compression_ratio')),
                'breakout_date': res.get('breakout_date'),
                'breakout_price': cls._clean_value(res.get('breakout_close')), # 'breakout_price' from DDL might be close
                'breakout_high': cls._clean_value(res.get('breakout_high')),
                'breakout_volume': cls._clean_value(res.get('breakout_volume')),
                'breakout_strength': cls._clean_value(res.get('breakout_strength_vs_pattern_high')),
                'volume_surge_ratio': cls._clean_value(res.get('volume_surge_ratio')),
                'sma_50': cls._clean_value(res.get('sma_50')),
                'sma_150': cls._clean_value(res.get('sma_150')), # Placeholder, script doesn't calculate this
                'sma_200': cls._clean_value(res.get('sma_200')),
                'atr': cls._clean_value(res.get('atr_50')), # Using atr_50 from screener
                'entry_price': cls._clean_value(res.get('entry_price')),
                'suggested_stop_loss': cls._clean_value(res.get('suggested_stop_loss')),
                'suggested_take_profit': cls._clean_value(res.get('suggested_take_profit')),
                'risk_reward_ratio': cls._clean_value(res.get('risk_reward_ratio')),
                'duration_score': res.get('duration_score'),
                'contraction_score': res.get('contraction_score'),
                'compression_score': res.get('compression_score'),
                'volume_score': res.get('volume_score'),
                'prior_uptrend_gain': cls._clean_value(res.get('prior_uptrend_gain_pct')),
                'price_breakout': bool(res.get('price_breakout')) if res.get('price_breakout') is not None else None,
                'volume_surge': bool(res.get('volume_surge')) if res.get('volume_surge') is not None else None,
                'green_breakout_candle': bool(res.get('green_breakout_candle')) if res.get('green_breakout_candle') is not None else None,
                'above_sma50': bool(res.get('above_sma50')) if res.get('above_sma50') is not None else None,
                'above_sma100': bool(res.get('above_sma100')) if res.get('above_sma100') is not None else None,
                'change_pct': cls._clean_value(res.get('change', 0.0)),
                'additional_metrics': json.dumps({ # Example of what could be in jsonb
                    'contraction_details': res.get('contraction_details', []),
                    'pattern_weekly_breakdown': res.get('pattern_weekly_breakdown', []),
                }, default=str),
                'run_time': now,
                'created_at': now
            }
            records_to_insert.append(record)

            # Ensure all numpy scalar types are converted for the current record
            import numpy as np
            for key, val in record.items():
                if isinstance(val, np.generic):
                    record[key] = cls._clean_value(val)

            # Look up instrument_token if missing
            if not record['instrument_token']:
                try:
                    # Check cursor state before token lookup
                    if cur.closed:
                        logger.warning(f"Cursor closed during token lookup for {record['symbol']}")
                        record['instrument_token'] = -1
                        continue
                        
                    cur.execute("SELECT instrument_token FROM equity_tokens WHERE tradingsymbol = %s LIMIT 1;", (record['symbol'],))
                    token_row = cur.fetchone()
                    if token_row:
                        # If cursor returns list/tuple/dict depending on cursor factory
                        if isinstance(token_row, dict):
                            record['instrument_token'] = token_row.get('instrument_token')
                        else:
                            record['instrument_token'] = token_row[0]
                except Exception as e:
                    logger.warning(f"Could not fetch instrument_token for symbol {record['symbol']}: {e}")
            # Default to -1 if still None to satisfy NOT NULL constraint
            if record['instrument_token'] is None:
                record['instrument_token'] = -1

        try:
            # Final cursor check before batch insert
            if cur.closed:
                logger.error("Cursor closed before batch insert operation")
                raise Exception("Database cursor was closed before batch insert")
                
            logger.info(f"Attempting to batch insert {len(records_to_insert)} advanced VCP results.")
            cur.executemany(insert_query, records_to_insert)
            logger.info(f"Successfully inserted {cur.rowcount} records into advanced_vcp_results.")
        except Exception as e:
            logger.error(f"Error during batch insert into advanced_vcp_results: {e}", exc_info=True)
            raise

    @classmethod
    def delete_all(cls, cur):
        """
        Delete all rows from the advanced_vcp_results table.
        """
        # Check if cursor is valid before proceeding
        if cur.closed:
            logger.error("Cursor is closed - cannot delete from advanced_vcp_results")
            raise Exception("Database cursor is closed")
            
        delete_query = "DELETE FROM advanced_vcp_results;"
        try:
            cur.execute(delete_query)
            logger.info("Deleted all records from advanced_vcp_results table.")
        except Exception as e:
            logger.error(f"Error deleting from advanced_vcp_results: {e}", exc_info=True)
            raise

    @classmethod
    def fetch_all(cls, cur):
        """
        Fetch all records from the advanced_vcp_results table.
        """
        select_query = "SELECT * FROM advanced_vcp_results ORDER BY quality_score DESC, run_time DESC;"
        try:
            # Check if cursor is closed before executing
            if cur.closed:
                logger.error("Cursor is already closed before executing query")
                return []
            
            cur.execute(select_query)
            
            # Check if cursor description is None (query failed)
            if cur.description is None:
                logger.warning("Query executed but no description available - likely no results or query failed")
                return []
            
            # Check if cursor is still open before fetching
            if cur.closed:
                logger.error("Cursor was closed after execute but before fetchall")
                return []
            
            # Fetch column names from cursor description
            colnames = [desc[0] for desc in cur.description]
            
            # Fetch all rows with additional error handling
            try:
                rows = cur.fetchall()
                if not rows:
                    logger.info("No records found in advanced_vcp_results table")
                    return []
                
                # Convert rows to dictionaries
                result_rows = [dict(zip(colnames, row)) for row in rows]
                
            except Exception as fetch_error:
                if "cursor already closed" in str(fetch_error):
                    logger.error("Cursor was closed during fetchall operation")
                    return []
                else:
                    raise fetch_error
            
            # Convert datetime objects to strings for JSON serialization
            for row in result_rows:
                for key, value in row.items():
                    if isinstance(value, datetime):
                        row[key] = value.isoformat()
                    elif hasattr(value, '__class__') and 'Decimal' in str(type(value)):
                        # Convert Decimal to float for JSON serialization
                        row[key] = float(value)
            
            logger.info(f"Fetched {len(result_rows)} records from advanced_vcp_results.")
            return result_rows
            
        except Exception as e:
            logger.error(f"Error fetching from advanced_vcp_results: {e}", exc_info=True)
            return [] 