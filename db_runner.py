import sqlite3
import time
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional

DB_PATH = "prop_mgmt.db"
MAX_ROWS = 1000

@dataclass
class SQLResult:
    success:bool
    df:Optional[pd.DataFrame]=None
    row_count:int=0
    execution_time:float=0.0
    error_type:Optional[str]=None
    error_message: Optional[str] = None
    sql_executed: Optional[str] = None
    truncated: bool = False  

def calculate_execution_time(start:float)->float:
    return round((time.perf_counter() - start) * 1000, 1)

def classify_error(error_text:str)->str:
    text = error_text.lower()
    if "syntax error" in text:
        return "There is a syntax error. Try rephasing your question."
    if "no such table" in text:
        return "The query references a table which does not exist."
    if "no such column" in text:
        return "The query references a column which does not exist."
    if "ambiguous column" in text:
        return "A column name appears in more than one table without a table alias."
    if "no such function" in text:
        return "The query used a SQL function that SQLite doesn't support."
    return "query_error"

def run_query(sql:str,db_path=DB_PATH)-> SQLResult:
    start_time = time.perf_counter()
    try:
        con = sqlite3.connect(db_path, check_same_thread=False)
    except Exception as e: 
        elapsed=calculate_execution_time(start_time)
        return SQLResult(
        success=False,
        error_type="connection_error",
        error_message="Could not connect to Database",
        sql_executed=sql,
        execution_time=elapsed
    )
    try:
        df=pd.read_sql_query(sql,con)
    except pd.errors.DatabaseError as e:
        elapsed=calculate_execution_time(start_time)
        con.close()
        return SQLResult(
            success=False,
            error_type=classify_error(str(e)),
            error_message=classify_error(str(e)),
            sql_executed=sql,
            execution_time=elapsed,
        )
    
    finally:
        con.close()
    elapsed=calculate_execution_time(start_time)
    if df.empty:
        return SQLResult(
            success=True,
            df=df,
            row_count=0,
            execution_time=elapsed,
            sql_executed=sql
        )
        
    truncated=False
    if len(df)>MAX_ROWS:
        df=df.head(MAX_ROWS)
        truncated=True

    df.columns=[str(col).strip() for col in df.columns]

    return SQLResult(
        success=True,
        df=df,
        row_count=len(df),
        execution_time=elapsed,
        sql_executed=sql,
        truncated=truncated
    )

if __name__ == "__main__":
    result = run_query("SELECT property_name FROM property ORDER BY property_name")
    print("basic query:", result.row_count, "rows,", result.execution_time, "ms")
    print(result.df)

    result = run_query("SELECT banana FROM property WHERE property_id = 1")
    print(result.error_message)

    result = run_query("SELECT * FROM lease WHERE lease_id = -999")
    print("\nempty result — success:", result.success, "| rows:", result.row_count)