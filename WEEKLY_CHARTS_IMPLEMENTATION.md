# Weekly Charts Implementation

## Overview
This document summarizes the changes made to properly handle weekly charts in the VCP Trader application. Weekly charts require special handling because they represent data aggregated over a calendar week, unlike daily charts where each trading day has its own candle.

## Key Concepts

### Weekly Candle Logic
- Weekly candles represent a calendar week, not just trading days
- A candle starts on the first trading day of a week
- The same candle is updated throughout the week until the next week begins
- ISO calendar week numbers determine week boundaries

### Implementation Details

1. **Scheduler Optimization**
   - Changed weekly VCP screener to run every 5 minutes instead of every minute
   - Reduced `max_instances` from 3 to 2 for weekly screener jobs
   - This reduces computational load while maintaining timely updates

2. **Week Transition Detection**
   - Enhanced `is_new_week()` function to compare ISO week numbers
   - Properly handles year transitions (week 1 of new year vs week 52/53 of previous year)
   - Handles weekends and holidays naturally within the week concept

3. **Candle Update Logic**
   - If in same week: Update existing candle's high/low/close with new price data
   - If in new week: Create a new candle with current price as OHLC values
   - Original weekly open price is preserved throughout the week

4. **Technical Indicator Recalculation**
   - Indicators (SMAs, ATR, 52-week high/low) are recalculated after candle updates
   - Ensures accurate screening based on the latest price information
   - Handles partial data gracefully with appropriate window sizes

5. **Partial Week Handling**
   - Added logic to identify stocks with partial data from the current week
   - Ensures proper continuation of ongoing weekly candles
   - Prevents inappropriate creation of new candles

## Modified Files

1. **schedulers.py**
   - Updated cron schedules for weekly VCP screener to run every 5 minutes
   - Reduced max_instances to avoid overloading the system

2. **get_screener.py**
   - Enhanced `is_new_week()` function with better documentation
   - Improved `update_weekly_live_data()` function to handle weekly candle updates
   - Enhanced `load_precomputed_weekly_ohlc()` to track partial week data
   - Updated `run_weekly_vcp_screener()` function with better documentation

## Edge Cases Addressed

1. **Weekend Gaps**
   - Handled through ISO week number transitions
   - Friday's close and Monday's open naturally fall in different weekly candles

2. **Mid-Week Holidays**
   - Trading days before and after a holiday within the same week use the same candle
   - Preserves the open from the first trading day of the week

3. **Initial Load with Partial Week**
   - System checks for and identifies stocks with data from the current week
   - Properly updates those candles instead of creating new ones

4. **Year Transitions**
   - Handled through ISO week number comparison including year
   - Week 1 of a new year properly starts a new candle

## Testing Recommendations

1. Test transitions between weeks
2. Verify that mid-week holidays don't break weekly candles
3. Confirm technical indicators are correctly recalculated
4. Check performance impact of the reduced scheduler frequency 