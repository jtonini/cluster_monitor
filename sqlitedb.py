#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sqlitedb.py - Extended SQLite database operations
Part of hpclib - included for standalone operation
"""
import typing
from typing import *

import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime


class SQLiteDB:
    """Extended SQLite database operations"""
    
    def __init__(self, db_path: str):
        """
        Initialize database connection
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = str(db_path)
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()
    
    def backup(self, backup_path: str) -> bool:
        """
        Backup database to another file
        
        Args:
            backup_path: Path for backup file
            
        Returns:
            True if successful
        """
        try:
            backup_conn = sqlite3.connect(backup_path)
            self.connection.backup(backup_conn)
            backup_conn.close()
            return True
        except Exception as e:
            print(f"Backup error: {e}")
            return False
    
    def vacuum(self):
        """Vacuum database to reclaim space"""
        self.cursor.execute('VACUUM')
        self.connection.commit()
    
    def analyze(self):
        """Analyze database for query optimization"""
        self.cursor.execute('ANALYZE')
        self.connection.commit()
    
    def get_size(self) -> int:
        """Get database file size in bytes"""
        return Path(self.db_path).stat().st_size
    
    def get_table_info(self, table_name: str) -> list:
        """Get detailed table information"""
        self.cursor.execute(f"PRAGMA table_info({table_name})")
        return self.cursor.fetchall()
    
    def get_indexes(self, table_name: str = None) -> list:
        """Get list of indexes"""
        if table_name:
            query = f"SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='{table_name}'"
        else:
            query = "SELECT name FROM sqlite_master WHERE type='index'"
        self.cursor.execute(query)
        return [row[0] for row in self.cursor.fetchall()]
    
    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()


if __name__ == '__main__':
    # Test the module
    db = SQLiteDB(':memory:')
    db.close()
    print("SQLiteDB module loaded successfully")
