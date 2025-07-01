import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ScreenerResult:
    """
    Model for interacting with the screener_results table.
    Each record represents one 'hit' or passing result of a screener (e.g. VCP, IPO).
    """

    def __init__(
        self,
        screener_name,
        instrument_token,
        symbol,
        last_price=0.0,
        change_pct=0.0,
        sma_50=0.0,
        sma_100=0.0,
        sma_200=0.0,
        atr=0.0,
        run_time=None,
    ):
        self.screener_name = screener_name
        self.instrument_token = instrument_token
        self.symbol = symbol
        self.last_price = last_price
        self.change_pct = change_pct
        self.sma_50 = sma_50
        self.sma_100 = sma_100
        self.sma_200 = sma_200
        self.atr = atr
        # Default to "now" if run_time is not given
        self.run_time = run_time if run_time else datetime.now()

    def save(self, cur):
        """
        Save this record into the screener_results table.
        """
        insert_query = """
            INSERT INTO screener_results (
                screener_name,
                instrument_token,
                symbol,
                last_price,
                change_pct,
                sma_50,
                sma_100,
                sma_200,
                atr,
                run_time
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        try:
            cur.execute(
                insert_query,
                (
                    self.screener_name,
                    self.instrument_token,
                    self.symbol,
                    self.last_price,
                    self.change_pct,
                    self.sma_50,
                    self.sma_100,
                    self.sma_200,
                    self.atr,
                    self.run_time
                )
            )
        except Exception as e:
            logger.error(f"Error saving screener result: {e}")
            raise e

    @classmethod
    def delete_all_by_screener(cls, cur, screener_name):
        """
        Delete all rows for a specific screener_name, e.g. 'vcp', 'ipo', etc.
        Useful if you're clearing out old results before running a new pass.
        """
        delete_query = """
            DELETE FROM screener_results
            WHERE screener_name = %s;
        """
        try:
            cur.execute(delete_query, (screener_name,))
            logger.info(f"Deleted all screener_results for screener: {screener_name}")
        except Exception as e:
            logger.error(f"Error deleting screener_results for {screener_name}: {e}")
            raise e

    @classmethod
    def fetch_by_screener(cls, cur, screener_name):
        """
        Fetch the most recent records for a particular screener.
        You can customize this as needed to limit or sort results.
        """
        select_query = f"""
            SELECT
                screener_name,
                instrument_token,
                symbol,
                last_price,
                change_pct,
                sma_50,
                sma_100,
                sma_200,
                atr,
                run_time
            FROM screener_results
            WHERE screener_name = %s
            ORDER BY run_time DESC;
        """
        try:
            cur.execute(select_query, (screener_name,))
            rows = cur.fetchall()
            logger.info(f"Fetched {len(rows)} screener_results for screener: {screener_name}")
            return rows
        except Exception as e:
            logger.error(f"Error fetching screener_results for {screener_name}: {e}")
            raise e

    @classmethod
    def batch_save(cls, cur, results):
        """
        Save multiple screener results in batch, with a single log message at the end.
        
        Args:
            cur: Database cursor
            results: List of ScreenerResult objects
        """
        if not results:
            logger.info("No screener results to save")
            return
            
        count = 0
        screener_name = results[0].screener_name if results else None
        
        try:
            for result in results:
                result.save(cur)
                count += 1
                
            logger.info(f"[{screener_name}] Saved {count} screener results")
            
            # Send NOTIFY to trigger the socket subscription update for newly added stocks
            cur.execute("NOTIFY data_changed, 'screener_results'")
            logger.info("Sent NOTIFY data_changed for screener_results")
        except Exception as e:
            logger.error(f"Error in batch save of screener results: {e}")
            raise e
