#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
urdb.py - Universal Database wrapper for SQLite
Part of hpclib - included for standalone operation
"""
import typing
from typing import *

import os
import sys
import sqlite3
from pathlib import Path


class URdb:
    """Universal Database wrapper for SQLite operations"""
    
    def __init__(self, db_path: str):
        """
        Initialize database connection
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = str(db_path)
        self.connection = None
        self.cursor = None
        self._connect()
    
    def _connect(self):
        """Establish database connection"""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row  # Enable column access by name
            self.cursor = self.connection.cursor()
        except sqlite3.Error as e:
            raise Exception(f"Database connection error: {e}")
    
    def execute(self, query: str, parameters: tuple = None):
        """
        Execute a SQL query
        
        Args:
            query: SQL query string
            parameters: Query parameters (optional)
            
        Returns:
            Cursor object for SELECT queries, self for others
        """
        try:
            if parameters:
                self.cursor.execute(query, parameters)
            else:
                self.cursor.execute(query)
            
            # Auto-commit for non-SELECT queries
            if not query.strip().upper().startswith('SELECT'):
                self.connection.commit()
            
            return self.cursor
        
        except sqlite3.Error as e:
            self.connection.rollback()
            raise Exception(f"Query execution error: {e}\nQuery: {query}")
    
    def executemany(self, query: str, parameters: list):
        """
        Execute a SQL query multiple times with different parameters
        
        Args:
            query: SQL query string
            parameters: List of parameter tuples
            
        Returns:
            self
        """
        try:
            self.cursor.executemany(query, parameters)
            self.connection.commit()
            return self
        except sqlite3.Error as e:
            self.connection.rollback()
            raise Exception(f"Query execution error: {e}")
    
    def fetchone(self):
        """Fetch one row from last query"""
        return self.cursor.fetchone()
    
    def fetchall(self):
        """Fetch all rows from last query"""
        return self.cursor.fetchall()
    
    def fetchmany(self, size: int = None):
        """Fetch multiple rows from last query"""
        if size:
            return self.cursor.fetchmany(size)
        return self.cursor.fetchmany()
    
    def commit(self):
        """Commit current transaction"""
        self.connection.commit()
    
    def rollback(self):
        """Rollback current transaction"""
        self.connection.rollback()
    
    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()
    
    def __del__(self):
        """Destructor"""
        self.close()
    
    @property
    def lastrowid(self):
        """Get last inserted row ID"""
        return self.cursor.lastrowid
    
    @property
    def rowcount(self):
        """Get number of affected rows"""
        return self.cursor.rowcount
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists"""
        result = self.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        ).fetchone()
        return result is not None
    
    def get_tables(self) -> list:
        """Get list of all tables"""
        result = self.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        return [row[0] for row in result]
    
    def get_columns(self, table_name: str) -> list:
        """Get list of columns for a table"""
        result = self.execute(f"PRAGMA table_info({table_name})").fetchall()
        return [row[1] for row in result]


if __name__ == '__main__':
    # Test the module
    db = URdb(':memory:')
    db.execute('CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)')
    db.execute('INSERT INTO test (name) VALUES (?)', ('Test',))
    result = db.execute('SELECT * FROM test').fetchone()
    print(f"Test result: {dict(result)}")
    db.close()
