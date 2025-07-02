import asyncio
import logging
import os
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
import aiopg
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class AsyncDatabaseManager:
    """Async database connection manager for non-blocking operations"""
    
    def __init__(self):
        self.pools: Dict[str, aiopg.Pool] = {}
        self.connection_params = {
            'host': os.getenv("DB_HOST"),
            'port': int(os.getenv("DB_PORT", 5432)),
            'user': os.getenv("DB_USER"),
            'password': os.getenv("DB_PASSWORD"),
            'database': os.getenv("DB_NAME"),
            'connect_timeout': 10,
            'application_name': 'vcpTrader_async',
            'keepalives_idle': 600,
            'keepalives_interval': 30,
            'keepalives_count': 3,
            # SSL configuration - disable SSL for localhost connections
            'sslmode': os.getenv("DB_SSLMODE", "disable" if os.getenv("DB_HOST") == "localhost" else "prefer")
        }
    
    async def initialize_pools(self):
        """Initialize connection pools for different types of operations"""
        try:
            # Main pool for general API operations (higher concurrency)
            self.pools['main'] = await aiopg.create_pool(
                minsize=5,
                maxsize=25,  # Increased from 15 to handle more concurrent requests
                **self.connection_params
            )
            
            # Read-only pool for data fetching (optimized for reads)
            self.pools['readonly'] = await aiopg.create_pool(
                minsize=3,
                maxsize=15,
                **self.connection_params
            )
            
            # Heavy operations pool (limited to prevent resource exhaustion)
            self.pools['heavy'] = await aiopg.create_pool(
                minsize=1,
                maxsize=5,
                **self.connection_params
            )
            
            logger.info("Async database pools initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize async database pools: {e}")
            raise
    
    @asynccontextmanager
    async def get_connection(self, pool_name: str = 'main'):
        """Get an async database connection from the specified pool"""
        if pool_name not in self.pools:
            raise ValueError(f"Unknown pool: {pool_name}")
        
        pool = self.pools[pool_name]
        async with pool.acquire() as conn:
            try:
                yield conn
            except Exception as e:
                # Rollback on error
                try:
                    await conn.rollback()
                except:
                    pass
                raise e
    
    async def execute_query(self, query: str, params: tuple = None, 
                          pool_name: str = 'main', fetch: str = 'all') -> Optional[List[Dict]]:
        """Execute a query and return results"""
        async with self.get_connection(pool_name) as conn:
            async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                await cur.execute(query, params)
                
                if fetch == 'all':
                    result = await cur.fetchall()
                    return [dict(row) for row in result] if result else []
                elif fetch == 'one':
                    result = await cur.fetchone()
                    return dict(result) if result else None
                elif fetch == 'none':
                    return None
                else:
                    raise ValueError(f"Invalid fetch type: {fetch}")
    
    async def execute_transaction(self, queries: List[tuple], pool_name: str = 'main') -> bool:
        """Execute multiple queries in a transaction"""
        async with self.get_connection(pool_name) as conn:
            async with conn.cursor() as cur:
                try:
                    for query, params in queries:
                        await cur.execute(query, params)
                    await conn.commit()
                    return True
                except Exception as e:
                    await conn.rollback()
                    logger.error(f"Transaction failed: {e}")
                    raise
    
    async def close_pools(self):
        """Close all connection pools"""
        for name, pool in self.pools.items():
            try:
                pool.close()
                await pool.wait_closed()
                logger.info(f"Closed {name} pool")
            except Exception as e:
                logger.error(f"Error closing {name} pool: {e}")
        
        self.pools.clear()

# Global async database manager instance
async_db = AsyncDatabaseManager()

async def get_async_db() -> AsyncDatabaseManager:
    """Dependency to get async database manager"""
    return async_db

# Context managers for different operation types
@asynccontextmanager
async def get_main_connection():
    """Get connection for general API operations"""
    async with async_db.get_connection('main') as conn:
        yield conn

@asynccontextmanager
async def get_readonly_connection():
    """Get connection for read-only operations"""
    async with async_db.get_connection('readonly') as conn:
        yield conn

@asynccontextmanager
async def get_heavy_connection():
    """Get connection for heavy operations (limited pool)"""
    async with async_db.get_connection('heavy') as conn:
        yield conn 