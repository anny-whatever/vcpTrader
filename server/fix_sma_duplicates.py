#!/usr/bin/env python3
"""
Fix SMA Duplicates Script - Updated

This script addresses the choppy SMA line issue by:
1. Removing duplicate OHLC entries from the database
2. Adding a unique constraint to prevent future duplicates
3. Verifying the cleanup was successful

Run this script from the server directory:
    cd /var/www/vcpTrader/server
    python3 fix_sma_duplicates.py
"""

import sys
import os
import logging
from pathlib import Path

# Add src to Python path
sys.path.append('src')

try:
    from db import get_db_connection, release_main_db_connection
except ImportError as e:
    print(f"Error importing database modules: {e}")
    print("Make sure you're running this from the server directory")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def execute_sql_cleanup():
    """Execute the SQL cleanup script"""
    logger.info("Starting SMA duplicates cleanup...")
    
    # Read the simplified SQL script
    sql_file = Path(__file__).parent / "fix_sma_duplicates_simple.sql"
    try:
        with open(sql_file, 'r') as file:
            sql_content = file.read()
    except FileNotFoundError:
        logger.error(f"SQL file not found: {sql_file}")
        return False
    
    conn, cur = None, None
    try:
        # Get database connection
        conn, cur = get_db_connection()
        logger.info("Connected to database")
        
        # Split SQL by lines and execute each SELECT/CREATE/INSERT separately
        lines = sql_content.split('\n')
        current_statement = []
        statement_count = 0
        
        for line in lines:
            line = line.strip()
            
            # Skip comments and empty lines
            if line.startswith('--') or not line:
                continue
                
            current_statement.append(line)
            
            # Execute when we hit a semicolon
            if line.endswith(';'):
                statement = ' '.join(current_statement)
                current_statement = []
                
                if statement.strip():
                    try:
                        statement_count += 1
                        logger.info(f"Executing statement {statement_count}: {statement[:50]}...")
                        cur.execute(statement)
                        
                        # Fetch results for SELECT statements
                        if statement.strip().upper().startswith('SELECT'):
                            results = cur.fetchall()
                            if results:
                                for row in results:
                                    logger.info(f"  Result: {row}")
                        
                        # Commit after each statement for safety
                        conn.commit()
                        
                    except Exception as e:
                        logger.error(f"Error executing statement: {e}")
                        logger.error(f"Statement was: {statement}")
                        conn.rollback()
                        return False
        
        logger.info("All statements executed successfully")
        
        # Try to add unique constraint
        try:
            logger.info("Adding unique constraint...")
            cur.execute("""
                ALTER TABLE ohlc 
                ADD CONSTRAINT ohlc_unique_entry 
                UNIQUE (instrument_token, symbol, interval, date)
            """)
            conn.commit()
            logger.info("✅ Unique constraint added successfully")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("✅ Unique constraint already exists (this is OK)")
            else:
                logger.warning(f"Could not add unique constraint: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Database error: {e}")
        if conn:
            conn.rollback()
        return False
        
    finally:
        if conn and cur:
            release_main_db_connection(conn, cur)
            logger.info("Database connection closed")

def verify_cleanup():
    """Verify that the cleanup was successful"""
    logger.info("Verifying cleanup results...")
    
    conn, cur = None, None
    try:
        conn, cur = get_db_connection()
        
        # Check for remaining duplicates
        cur.execute("""
            SELECT 
                symbol, 
                date::date, 
                COUNT(*) as count 
            FROM ohlc 
            WHERE date >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY symbol, date::date 
            HAVING COUNT(*) > 1 
            LIMIT 5
        """)
        
        duplicates = cur.fetchall()
        if duplicates:
            logger.warning("Still found some duplicates:")
            for dup in duplicates:
                logger.warning(f"  {dup[0]} on {dup[1]}: {dup[2]} entries")
            return False
        else:
            logger.info("✅ No duplicates found - cleanup successful!")
            return True
            
    except Exception as e:
        logger.error(f"Error during verification: {e}")
        return False
        
    finally:
        if conn and cur:
            release_main_db_connection(conn, cur)

def main():
    """Main function"""
    print("🔧 SMA Duplicates Fix Script - Updated")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists('src'):
        print("❌ Error: Please run this script from the server directory")
        print("   cd /var/www/vcpTrader/server")
        print("   python3 fix_sma_duplicates.py")
        sys.exit(1)
    
    # Check if SQL file exists
    sql_file = Path(__file__).parent / "fix_sma_duplicates_simple.sql"
    if not sql_file.exists():
        print(f"❌ Error: SQL file not found: {sql_file}")
        sys.exit(1)
    
    print("⚠️  WARNING: This will modify the OHLC table!")
    print("   - Duplicate entries will be removed")
    print("   - A backup of 1000 sample records will be created")
    print("   - A unique constraint will be added")
    
    response = input("\nContinue? (y/N): ").strip().lower()
    if response != 'y':
        print("❌ Operation cancelled by user")
        sys.exit(0)
    
    # Execute cleanup
    logger.info("Step 1: Executing database cleanup")
    success = execute_sql_cleanup()
    
    if success:
        logger.info("Step 2: Verifying cleanup")
        verification_success = verify_cleanup()
        
        if verification_success:
            print("\n✅ SUCCESS: SMA duplicates have been fixed!")
            print("\nNext steps:")
            print("1. The frontend charts should now show smooth SMA lines")
            print("2. The database now has a unique constraint to prevent future duplicates")
            print("3. You may want to restart your application to clear any cached data")
        else:
            print("\n⚠️  WARNING: Cleanup completed but verification found issues")
            print("You may need to run the script again or check the logs")
    else:
        print("\n❌ ERROR: Cleanup failed")
        print("Please check the logs above for details")
        sys.exit(1)

if __name__ == "__main__":
    main() 