"""
数据库工具 - SQLite数据库操作
"""

import sqlite3
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from contextlib import contextmanager
from .base import BaseTool, ToolResult, ToolStatus


class SQLiteTool(BaseTool):
    """SQLite数据库工具"""
    
    name: str = "sqlite"
    description: str = """Execute SQL queries on SQLite databases.
    
Operations:
- query: Execute SELECT query and return results
- execute: Execute INSERT/UPDATE/DELETE statements
- create_table: Create a new table
- list_tables: List all tables
- describe: Get table schema
- import_data: Import data from list of dicts

Use for local data storage and querying."""

    parameters: Dict[str, Any] = {
        "properties": {
            "action": {
                "type": "string",
                "enum": ["query", "execute", "create_table", "list_tables", "describe", "import_data"],
                "description": "Operation to perform"
            },
            "database": {
                "type": "string",
                "description": "Path to SQLite database file",
                "default": "data/database.db"
            },
            "sql": {
                "type": "string",
                "description": "SQL query or statement"
            },
            "params": {
                "type": "array",
                "description": "Query parameters"
            },
            "table": {
                "type": "string",
                "description": "Table name (for describe/import_data)"
            },
            "data": {
                "type": "array",
                "description": "Data to import (list of dicts)"
            }
        },
        "required": ["action"]
    }
    
    @contextmanager
    def _get_connection(self, db_path: str):
        """获取数据库连接"""
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    async def execute(
        self,
        action: str,
        database: str = "data/database.db",
        sql: str = None,
        params: List = None,
        table: str = None,
        data: List[Dict] = None,
        **kwargs
    ) -> ToolResult:
        """执行数据库操作"""
        try:
            with self._get_connection(database) as conn:
                if action == "query":
                    return self._query(conn, sql, params)
                elif action == "execute":
                    return self._execute_sql(conn, sql, params)
                elif action == "create_table":
                    return self._create_table(conn, sql)
                elif action == "list_tables":
                    return self._list_tables(conn)
                elif action == "describe":
                    return self._describe(conn, table)
                elif action == "import_data":
                    return self._import_data(conn, table, data)
                else:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        output=None,
                        error=f"Unknown action: {action}"
                    )
                    
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                output=None,
                error=f"Database error: {str(e)}"
            )
    
    def _query(self, conn, sql: str, params: List = None) -> ToolResult:
        """执行查询"""
        cursor = conn.cursor()
        cursor.execute(sql, params or [])
        
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = [dict(row) for row in cursor.fetchall()]
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            output=rows,
            metadata={"columns": columns, "row_count": len(rows)}
        )
    
    def _execute_sql(self, conn, sql: str, params: List = None) -> ToolResult:
        """执行SQL语句"""
        cursor = conn.cursor()
        cursor.execute(sql, params or [])
        conn.commit()
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            output=f"Affected rows: {cursor.rowcount}",
            metadata={"rowcount": cursor.rowcount, "lastrowid": cursor.lastrowid}
        )
    
    def _create_table(self, conn, sql: str) -> ToolResult:
        """创建表"""
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            output="Table created successfully"
        )
    
    def _list_tables(self, conn) -> ToolResult:
        """列出所有表"""
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            output=tables
        )
    
    def _describe(self, conn, table: str) -> ToolResult:
        """获取表结构"""
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table})")
        
        columns = []
        for row in cursor.fetchall():
            columns.append({
                "name": row[1],
                "type": row[2],
                "nullable": not row[3],
                "default": row[4],
                "primary_key": bool(row[5])
            })
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            output=columns
        )
    
    def _import_data(self, conn, table: str, data: List[Dict]) -> ToolResult:
        """导入数据"""
        if not data:
            return ToolResult(
                status=ToolStatus.SUCCESS,
                output="No data to import"
            )
        
        columns = list(data[0].keys())
        placeholders = ", ".join(["?" for _ in columns])
        column_names = ", ".join(columns)
        
        sql = f"INSERT INTO {table} ({column_names}) VALUES ({placeholders})"
        
        cursor = conn.cursor()
        for row in data:
            values = [row.get(col) for col in columns]
            cursor.execute(sql, values)
        
        conn.commit()
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            output=f"Imported {len(data)} rows",
            metadata={"row_count": len(data)}
        )


class DataStoreTool(BaseTool):
    """简单数据存储工具 - 键值存储"""
    
    name: str = "data_store"
    description: str = """Simple key-value data storage.
    
Operations:
- get: Get value by key
- set: Set key-value pair
- delete: Delete key
- list: List all keys
- clear: Clear all data

Data persists in a JSON file."""

    parameters: Dict[str, Any] = {
        "properties": {
            "action": {
                "type": "string",
                "enum": ["get", "set", "delete", "list", "clear"],
                "description": "Operation to perform"
            },
            "key": {
                "type": "string",
                "description": "Storage key"
            },
            "value": {
                "type": ["string", "number", "object", "array", "boolean"],
                "description": "Value to store"
            },
            "store_file": {
                "type": "string",
                "description": "Storage file path",
                "default": "data/store.json"
            }
        },
        "required": ["action"]
    }
    
    def _load_store(self, path: str) -> Dict:
        """加载存储"""
        file_path = Path(path)
        if file_path.exists():
            content = file_path.read_text().strip()
            if content:
                return json.loads(content)
        return {}
    
    def _save_store(self, path: str, data: Dict):
        """保存存储"""
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    
    async def execute(
        self,
        action: str,
        key: str = None,
        value: Any = None,
        store_file: str = "data/store.json",
        **kwargs
    ) -> ToolResult:
        """执行存储操作"""
        try:
            store = self._load_store(store_file)
            
            if action == "get":
                result = store.get(key)
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    output=result
                )
            
            elif action == "set":
                store[key] = value
                self._save_store(store_file, store)
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    output=f"Stored key: {key}"
                )
            
            elif action == "delete":
                if key in store:
                    del store[key]
                    self._save_store(store_file, store)
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    output=f"Deleted key: {key}"
                )
            
            elif action == "list":
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    output=list(store.keys())
                )
            
            elif action == "clear":
                self._save_store(store_file, {})
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    output="Store cleared"
                )
            
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    output=None,
                    error=f"Unknown action: {action}"
                )
                
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                output=None,
                error=str(e)
            )


# 创建工具实例
sqlite_tool = SQLiteTool()
data_store = DataStoreTool()

