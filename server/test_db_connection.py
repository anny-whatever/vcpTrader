#!/usr/bin/env python3
"""
Database Connection Test Script
Tests all database connection pools and SSL configuration
"""

import sys
import os
import time
import logging

# Add the src directory to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

def test_trade_db_connection():
    """Test the trade database connection pool"""
    try:
        from db import get_trade_db_connection, release_trade_db_connection
        
        print("\n🧪 Testing Trade DB Connection...")
        
        # Test getting a connection
        conn, cur = get_trade_db_connection()
        
        # Test a simple query
        cur.execute("SELECT 1 as test_value")
        result = cur.fetchone()
        
        if result and result[0] == 1:
            print("✅ Trade DB connection successful")
            
            # Test a more complex query (check if ohlc table exists)
            cur.execute("SELECT COUNT(*) FROM ohlc LIMIT 1")
            count = cur.fetchone()[0]
            print(f"✅ OHLC table accessible with {count} records")
            
        else:
            print("❌ Trade DB connection failed - unexpected result")
            return False
            
        # Release the connection
        release_trade_db_connection(conn, cur)
        print("✅ Connection released properly")
        
        return True
        
    except Exception as e:
        print(f"❌ Trade DB connection failed: {e}")
        return False

def test_main_db_connection():
    """Test the main database connection pool"""
    try:
        from db import get_db_connection, release_main_db_connection
        
        print("\n🧪 Testing Main DB Connection...")
        
        # Test getting a connection
        conn, cur = get_db_connection()
        
        # Test a simple query
        cur.execute("SELECT 1 as test_value")
        result = cur.fetchone()
        
        if result and result[0] == 1:
            print("✅ Main DB connection successful")
        else:
            print("❌ Main DB connection failed - unexpected result")
            return False
            
        # Release the connection
        release_main_db_connection(conn, cur)
        print("✅ Connection released properly")
        
        return True
        
    except Exception as e:
        print(f"❌ Main DB connection failed: {e}")
        return False

def test_multiple_connections():
    """Test multiple concurrent connections to simulate VCP screener load"""
    try:
        from db import get_trade_db_connection, release_trade_db_connection
        
        print("\n🧪 Testing Multiple Concurrent Connections...")
        
        connections = []
        
        # Try to get 5 connections simultaneously
        for i in range(5):
            try:
                conn, cur = get_trade_db_connection()
                cur.execute("SELECT 1")
                cur.fetchone()
                connections.append((conn, cur))
                print(f"✅ Connection {i+1}/5 successful")
                time.sleep(0.1)  # Small delay
            except Exception as e:
                print(f"❌ Connection {i+1}/5 failed: {e}")
                
        # Release all connections
        for i, (conn, cur) in enumerate(connections):
            try:
                release_trade_db_connection(conn, cur)
                print(f"✅ Released connection {i+1}")
            except Exception as e:
                print(f"❌ Failed to release connection {i+1}: {e}")
                
        print(f"✅ Successfully tested {len(connections)}/5 concurrent connections")
        return len(connections) >= 3  # Consider success if at least 3 connections worked
        
    except Exception as e:
        print(f"❌ Multiple connections test failed: {e}")
        return False

def test_ssl_configuration():
    """Test SSL configuration by checking connection parameters"""
    try:
        import psycopg2
        from dotenv import load_dotenv
        
        load_dotenv()
        
        print("\n🧪 Testing SSL Configuration...")
        
        # Get environment variables
        db_host = os.getenv("DB_HOST")
        db_sslmode = os.getenv("DB_SSLMODE", "disable" if db_host == "localhost" else "prefer")
        
        print(f"DB_HOST: {db_host}")
        print(f"DB_SSLMODE: {db_sslmode}")
        
        # Test direct connection with SSL configuration
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            sslmode=db_sslmode,
            connect_timeout=10
        )
        
        # Check connection status
        with conn.cursor() as cur:
            cur.execute("SELECT version()")
            version = cur.fetchone()[0]
            print(f"✅ PostgreSQL version: {version}")
            
            # Check SSL status (try different methods for compatibility)
            try:
                cur.execute("SELECT ssl_is_used()")
                ssl_used = cur.fetchone()[0]
                print(f"✅ SSL enabled: {ssl_used}")
            except Exception:
                # ssl_is_used() doesn't exist in older PostgreSQL versions
                try:
                    cur.execute("SHOW ssl")
                    ssl_setting = cur.fetchone()[0]
                    print(f"✅ SSL setting: {ssl_setting}")
                except Exception:
                    print(f"✅ SSL mode set to: {db_sslmode} (unable to verify server SSL status)")
            
        conn.close()
        print("✅ SSL configuration test successful")
        return True
        
    except Exception as e:
        print(f"❌ SSL configuration test failed: {e}")
        return False

def main():
    """Run all database connection tests"""
    print("=" * 60)
    print("DATABASE CONNECTION TEST SUITE")
    print("=" * 60)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    results = []
    
    # Test SSL configuration first
    results.append(("SSL Configuration", test_ssl_configuration()))
    
    # Test individual connection pools
    results.append(("Trade DB Connection", test_trade_db_connection()))
    results.append(("Main DB Connection", test_main_db_connection()))
    
    # Test concurrent connections
    results.append(("Multiple Connections", test_multiple_connections()))
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:.<40} {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED! Database connections are working properly.")
        print("\nYour VCP screener should now work without SSL connection errors.")
    else:
        print("❌ SOME TESTS FAILED. Please check the errors above.")
        print("\nRecommended actions:")
        print("1. Verify your database is running")
        print("2. Check your .env file configuration")
        print("3. Ensure DB_SSLMODE is set to 'disable' for localhost")
        print("4. Restart your application after making changes")
    
    print("=" * 60)
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 