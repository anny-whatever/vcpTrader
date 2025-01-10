from db import get_client_db_connection, close_client_db_connection
import json
from decimal import Decimal
from datetime import datetime
from models import FetchPosition


def datetime_to_str(data):
    if isinstance(data, list):
        return [datetime_to_str(item) for item in data]
    elif isinstance(data, dict):
        return {key: datetime_to_str(value) for key, value in data.items()}
    elif isinstance(data, datetime):
        return data.isoformat()  
    return data

def decimal_to_float(data):
    if isinstance(data, list):
        return [decimal_to_float(item) for item in data]
    elif isinstance(data, dict):
        return {key: decimal_to_float(value) for key, value in data.items()}
    elif isinstance(data, Decimal):
        return float(data)
    return data


def get_positions():
    conn, cur = get_client_db_connection()
    try:
        positions_sabbo = FetchPosition.get_all_positions_sabbo(cur)
        positions_sabbo = decimal_to_float(positions_sabbo)
        positions_sabbo = datetime_to_str(positions_sabbo)
        
        positions_sutbo = FetchPosition.get_all_positions_sutbo(cur)
        positions_sutbo = decimal_to_float(positions_sutbo)
        positions_sutbo = datetime_to_str(positions_sutbo)  
        
        positions_danbo = FetchPosition.get_all_positions_danbo(cur)
        positions_danbo = decimal_to_float(positions_danbo)
        positions_danbo = datetime_to_str(positions_danbo)
        
        positions = []
        for position in positions_sabbo:
            positions.append(position)
        for position in positions_sutbo:
            positions.append(position)
        for position in positions_danbo:
            positions.append(position)
            
        return positions
    except Exception as e:
        print(f"Error fetching positions: {str(e)}")
        return []
    finally:
        close_client_db_connection()

def get_flags():
    conn, cur = get_client_db_connection()
    try:
        flags_sabbo = FetchPosition.get_all_flags_sabbo(cur)
        flags_sabbo = decimal_to_float(flags_sabbo)
        flags_sabbo = datetime_to_str(flags_sabbo)
        
        flags_sutbo = FetchPosition.get_all_flags_sutbo(cur)
        flags_sutbo = decimal_to_float(flags_sutbo)
        flags_sutbo = datetime_to_str(flags_sutbo)  
        
        flags_danbo = FetchPosition.get_all_flags_danbo(cur)
        flags_danbo = decimal_to_float(flags_danbo)
        flags_danbo = datetime_to_str(flags_danbo)
        
        flags = []
        for flag in flags_sabbo:
            flags.append(flag)
        for flag in flags_sutbo:
            flags.append(flag)
        for flag in flags_danbo:
            flags.append(flag)
            
        return flags
    except Exception as e:
        print(f"Error fetching flags: {str(e)}")
        return []
    finally:
        close_client_db_connection()

# get_flags()