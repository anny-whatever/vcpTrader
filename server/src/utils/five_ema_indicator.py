import logging

logger = logging.getLogger(__name__)

def get_indicators_5ema(df):
    """
    Compute the 5-period EMA and store it in a column 'EMA5'.
    Assumes 'close' column is present in the DataFrame.
    """
    try:
        import pandas_ta as ta
    except ImportError:
        logger.error("pandas_ta module not installed. Cannot compute EMA.")
        return df

    df['EMA5'] = ta.ema(df['close'], length=5)
    return df
