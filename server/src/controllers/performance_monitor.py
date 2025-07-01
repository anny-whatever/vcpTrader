from fastapi import APIRouter, HTTPException
from typing import Dict, List
import logging
import psutil
import os
from datetime import datetime, timedelta
import asyncio

from db import get_db_connection, close_db_connection
from controllers.optimized_schedulers import get_scheduler_status
from services.optimized_ohlc_collector import get_ohlc_collection_status
from services.optimized_risk_calculator import get_risk_calculation_status

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/performance/system")
async def get_system_performance():
    """
    Get current system performance metrics.
    """
    try:
        # Get CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # Get memory usage
        memory = psutil.virtual_memory()
        memory_info = {
            "total": memory.total,
            "available": memory.available,
            "percent": memory.percent,
            "used": memory.used
        }
        
        # Get disk usage
        disk_usage = psutil.disk_usage('/')
        disk_info = {
            "total": disk_usage.total,
            "used": disk_usage.used,
            "free": disk_usage.free,
            "percent": (disk_usage.used / disk_usage.total) * 100
        }
        
        # Get process information for the current Python process
        current_process = psutil.Process(os.getpid())
        process_info = {
            "cpu_percent": current_process.cpu_percent(),
            "memory_percent": current_process.memory_percent(),
            "memory_info": current_process.memory_info()._asdict(),
            "num_threads": current_process.num_threads(),
            "connections": len(current_process.connections()),
            "create_time": datetime.fromtimestamp(current_process.create_time()).isoformat()
        }
        
        return {
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "percent": cpu_percent,
                "count": cpu_count
            },
            "memory": memory_info,
            "disk": disk_info,
            "process": process_info
        }
        
    except Exception as e:
        logger.error(f"Error getting system performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance/scheduler")
async def get_scheduler_performance():
    """
    Get scheduler status and task performance.
    """
    try:
        return get_scheduler_status()
    except Exception as e:
        logger.error(f"Error getting scheduler performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance/database")
async def get_database_performance():
    """
    Get database performance metrics.
    """
    try:
        conn, cur = get_db_connection()
        
        # Get database size information
        cur.execute("""
            SELECT 
                schemaname,
                tablename,
                attname,
                n_distinct,
                correlation
            FROM pg_stats 
            WHERE schemaname = 'public' 
            AND tablename IN ('ohlc', 'risk_scores', 'advanced_vcp_results')
            ORDER BY tablename, attname;
        """)
        
        stats_results = cur.fetchall()
        
        # Get table sizes
        cur.execute("""
            SELECT 
                tablename,
                pg_size_pretty(pg_total_relation_size(tablename::regclass)) as size,
                pg_total_relation_size(tablename::regclass) as size_bytes
            FROM (
                SELECT 'ohlc'::text as tablename
                UNION ALL SELECT 'risk_scores'::text
                UNION ALL SELECT 'advanced_vcp_results'::text
                UNION ALL SELECT 'screener_results'::text
            ) tables
            ORDER BY size_bytes DESC;
        """)
        
        size_results = cur.fetchall()
        
        # Get recent activity
        cur.execute("""
            SELECT 
                'ohlc' as table_name,
                COUNT(*) as total_rows,
                COUNT(DISTINCT symbol) as unique_symbols,
                MAX(date) as latest_date
            FROM ohlc
            WHERE date >= CURRENT_DATE - INTERVAL '7 days'
            
            UNION ALL
            
            SELECT 
                'risk_scores' as table_name,
                COUNT(*) as total_rows,
                COUNT(DISTINCT symbol) as unique_symbols,
                MAX(calculated_at) as latest_date
            FROM risk_scores
            WHERE calculated_at >= NOW() - INTERVAL '7 days'
            
            UNION ALL
            
            SELECT 
                'advanced_vcp_results' as table_name,
                COUNT(*) as total_rows,
                COUNT(DISTINCT symbol) as unique_symbols,
                MAX(created_at) as latest_date
            FROM advanced_vcp_results
            WHERE created_at >= NOW() - INTERVAL '7 days';
        """)
        
        activity_results = cur.fetchall()
        
        # Get connection information
        cur.execute("""
            SELECT 
                count(*) as total_connections,
                count(*) FILTER (WHERE state = 'active') as active_connections,
                count(*) FILTER (WHERE state = 'idle') as idle_connections
            FROM pg_stat_activity;
        """)
        
        connection_info = cur.fetchone()
        
        close_db_connection()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "table_sizes": [
                {
                    "table_name": row[0],
                    "size_pretty": row[1],
                    "size_bytes": row[2]
                }
                for row in size_results
            ],
            "recent_activity": [
                {
                    "table_name": row[0],
                    "total_rows": row[1],
                    "unique_symbols": row[2],
                    "latest_date": row[3].isoformat() if row[3] else None
                }
                for row in activity_results
            ],
            "connections": {
                "total": connection_info[0] if connection_info else 0,
                "active": connection_info[1] if connection_info else 0,
                "idle": connection_info[2] if connection_info else 0
            },
            "statistics": [
                {
                    "schema": row[0],
                    "table": row[1],
                    "column": row[2],
                    "distinct_values": row[3],
                    "correlation": row[4]
                }
                for row in stats_results
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting database performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance/tasks")
async def get_task_performance():
    """
    Get detailed task performance information.
    """
    try:
        # Get OHLC collection status
        try:
            ohlc_status = get_ohlc_collection_status()
        except:
            ohlc_status = {"error": "Unable to get OHLC status"}
        
        # Get risk calculation status
        try:
            risk_status = get_risk_calculation_status()
        except:
            risk_status = {"error": "Unable to get risk calculation status"}
        
        # Get VCP screener status from database
        conn, cur = get_db_connection()
        
        # Check advanced VCP results
        cur.execute("""
            SELECT 
                COUNT(*) as total_results,
                MAX(created_at) as latest_run,
                AVG(quality_score) as avg_quality_score
            FROM advanced_vcp_results
            WHERE created_at >= NOW() - INTERVAL '24 hours';
        """)
        vcp_result = cur.fetchone()
        
        # Check screener results
        cur.execute("""
            SELECT 
                screener_name,
                COUNT(*) as result_count,
                MAX(created_at) as latest_update
            FROM screener_results
            WHERE created_at >= NOW() - INTERVAL '24 hours'
            GROUP BY screener_name;
        """)
        screener_results = cur.fetchall()
        
        close_db_connection()
        
        vcp_status = {
            "total_results": vcp_result[0] if vcp_result else 0,
            "latest_run": vcp_result[1].isoformat() if vcp_result and vcp_result[1] else None,
            "avg_quality_score": float(vcp_result[2]) if vcp_result and vcp_result[2] else 0
        }
        
        return {
            "timestamp": datetime.now().isoformat(),
            "ohlc_collection": ohlc_status,
            "risk_calculation": risk_status,
            "vcp_screening": vcp_status,
            "screener_results": [
                {
                    "screener_name": row[0],
                    "result_count": row[1],
                    "latest_update": row[2].isoformat() if row[2] else None
                }
                for row in screener_results
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting task performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance/summary")
async def get_performance_summary():
    """
    Get a comprehensive performance summary.
    """
    try:
        # Get all performance data in parallel
        system_task = asyncio.create_task(get_system_performance())
        scheduler_task = asyncio.create_task(get_scheduler_performance())
        database_task = asyncio.create_task(get_database_performance())
        tasks_task = asyncio.create_task(get_task_performance())
        
        # Wait for all tasks to complete
        system_perf, scheduler_perf, db_perf, task_perf = await asyncio.gather(
            system_task, scheduler_task, database_task, tasks_task,
            return_exceptions=True
        )
        
        # Handle any exceptions
        if isinstance(system_perf, Exception):
            system_perf = {"error": str(system_perf)}
        if isinstance(scheduler_perf, Exception):
            scheduler_perf = {"error": str(scheduler_perf)}
        if isinstance(db_perf, Exception):
            db_perf = {"error": str(db_perf)}
        if isinstance(task_perf, Exception):
            task_perf = {"error": str(task_perf)}
        
        # Calculate health score
        health_score = calculate_health_score(system_perf, scheduler_perf, db_perf, task_perf)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "health_score": health_score,
            "system": system_perf,
            "scheduler": scheduler_perf,
            "database": db_perf,
            "tasks": task_perf
        }
        
    except Exception as e:
        logger.error(f"Error getting performance summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def calculate_health_score(system_perf: Dict, scheduler_perf: Dict, db_perf: Dict, task_perf: Dict) -> Dict:
    """
    Calculate an overall health score based on various metrics.
    """
    try:
        score = 100.0
        issues = []
        
        # System health checks
        if not isinstance(system_perf, dict) or "error" in system_perf:
            score -= 20
            issues.append("System metrics unavailable")
        else:
            # CPU usage
            cpu_percent = system_perf.get("cpu", {}).get("percent", 0)
            if cpu_percent > 80:
                score -= 15
                issues.append(f"High CPU usage: {cpu_percent}%")
            elif cpu_percent > 60:
                score -= 8
                issues.append(f"Moderate CPU usage: {cpu_percent}%")
            
            # Memory usage
            memory_percent = system_perf.get("memory", {}).get("percent", 0)
            if memory_percent > 85:
                score -= 15
                issues.append(f"High memory usage: {memory_percent}%")
            elif memory_percent > 70:
                score -= 8
                issues.append(f"Moderate memory usage: {memory_percent}%")
            
            # Process threads
            num_threads = system_perf.get("process", {}).get("num_threads", 0)
            if num_threads > 100:
                score -= 10
                issues.append(f"High thread count: {num_threads}")
            elif num_threads > 50:
                score -= 5
                issues.append(f"Moderate thread count: {num_threads}")
        
        # Scheduler health checks
        if not isinstance(scheduler_perf, dict) or "error" in scheduler_perf:
            score -= 15
            issues.append("Scheduler status unavailable")
        else:
            if not scheduler_perf.get("scheduler_running", False):
                score -= 20
                issues.append("Scheduler not running")
            
            # Check for stuck tasks
            task_status = scheduler_perf.get("task_status", {})
            for task_name, status in task_status.items():
                if status.get("running", False):
                    last_run = status.get("last_run")
                    if last_run:
                        last_run_time = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
                        if (datetime.now() - last_run_time).total_seconds() > 3600:  # 1 hour
                            score -= 10
                            issues.append(f"Task {task_name} may be stuck")
        
        # Database health checks
        if not isinstance(db_perf, dict) or "error" in db_perf:
            score -= 10
            issues.append("Database metrics unavailable")
        else:
            # Check for recent data
            recent_activity = db_perf.get("recent_activity", [])
            for activity in recent_activity:
                if activity["latest_date"] is None:
                    score -= 5
                    issues.append(f"No recent data in {activity['table_name']}")
                else:
                    latest_date = datetime.fromisoformat(activity["latest_date"].replace("Z", "+00:00"))
                    if (datetime.now() - latest_date).days > 1:
                        score -= 8
                        issues.append(f"Stale data in {activity['table_name']}")
        
        # Task performance checks
        if not isinstance(task_perf, dict) or "error" in task_perf:
            score -= 10
            issues.append("Task performance metrics unavailable")
        
        # Determine status
        if score >= 90:
            status = "Excellent"
        elif score >= 75:
            status = "Good"
        elif score >= 60:
            status = "Fair"
        elif score >= 40:
            status = "Poor"
        else:
            status = "Critical"
        
        return {
            "score": max(0, round(score, 1)),
            "status": status,
            "issues": issues,
            "recommendations": generate_recommendations(score, issues)
        }
        
    except Exception as e:
        logger.error(f"Error calculating health score: {e}")
        return {
            "score": 0,
            "status": "Unknown",
            "issues": ["Error calculating health score"],
            "recommendations": ["Check system logs for errors"]
        }

def generate_recommendations(score: float, issues: List[str]) -> List[str]:
    """Generate performance recommendations based on score and issues."""
    recommendations = []
    
    if score < 60:
        recommendations.append("Consider restarting the application to clear any stuck processes")
    
    if any("High CPU" in issue for issue in issues):
        recommendations.append("Reduce VCP screener frequency or enable process-based parallelization")
    
    if any("High memory" in issue for issue in issues):
        recommendations.append("Clear database connection pools and restart heavy tasks")
    
    if any("High thread" in issue for issue in issues):
        recommendations.append("Use the optimized scheduler to reduce thread usage")
    
    if any("Scheduler not running" in issue for issue in issues):
        recommendations.append("Restart the scheduler service")
    
    if any("stuck" in issue.lower() for issue in issues):
        recommendations.append("Kill stuck tasks and restart them")
    
    if any("Stale data" in issue for issue in issues):
        recommendations.append("Check OHLC data collection and API connectivity")
    
    if not recommendations:
        recommendations.append("System is performing well, continue monitoring")
    
    return recommendations

@router.post("/performance/optimize")
async def trigger_optimization():
    """
    Trigger performance optimization measures.
    """
    try:
        optimization_results = []
        
        # Clear any stuck tasks
        from controllers.optimized_schedulers import get_task_status, update_task_status
        task_status = get_task_status()
        
        for task_name, status in task_status.items():
            if status.get("running", False):
                last_run = status.get("last_run")
                if last_run:
                    last_run_time = datetime.fromisoformat(last_run)
                    if (datetime.now() - last_run_time).total_seconds() > 1800:  # 30 minutes
                        update_task_status(task_name, False)
                        optimization_results.append(f"Reset stuck task: {task_name}")
        
        # Force garbage collection
        import gc
        collected = gc.collect()
        optimization_results.append(f"Garbage collection freed {collected} objects")
        
        # Log current status
        optimization_results.append("Performance optimization completed")
        
        return {
            "timestamp": datetime.now().isoformat(),
            "optimizations_applied": optimization_results,
            "status": "completed"
        }
        
    except Exception as e:
        logger.error(f"Error during performance optimization: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 