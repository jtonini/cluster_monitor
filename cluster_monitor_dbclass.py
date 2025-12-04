#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cluster Monitor Database Class
Handles all database operations for cluster node monitoring
"""
import typing
from typing import *

import datetime
import os
import sys
from pathlib import Path

###
# From hpclib (included in repo)
###
from urdb import URdb


class ClusterMonitorDB:
    """Database operations for cluster monitoring"""
    
    def __init__(self, db_path: Path):
        """
        Initialize database connection
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.db = URdb(str(db_path))
    
    def init_schema(self, schema_file: Optional[Path] = None) -> None:
        """
        Initialize database schema
        
        Args:
            schema_file: Optional path to SQL schema file
        """
        if schema_file and schema_file.exists():
            # Load from schema file
            with open(schema_file, 'r') as f:
                sql_commands = f.read()
            
            # Execute each statement
            for statement in sql_commands.split(';'):
                if statement.strip():
                    self.db.execute(statement)
        else:
            # Use inline schema
            self._create_tables()
    
    def _create_tables(self) -> None:
        """Create database tables inline"""
        # Node status table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS node_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                cluster TEXT NOT NULL,
                node_name TEXT NOT NULL,
                status TEXT NOT NULL,
                slurm_state TEXT,
                is_available BOOLEAN NOT NULL,
                checked_from TEXT NOT NULL
            )
        """)
        
        # Node events table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS node_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                cluster TEXT NOT NULL,
                node_name TEXT NOT NULL,
                event_type TEXT NOT NULL,
                details TEXT,
                severity TEXT NOT NULL
            )
        """)
        
        # Recovery attempts table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS recovery_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                cluster TEXT NOT NULL,
                node_name TEXT NOT NULL,
                command TEXT NOT NULL,
                exit_code INTEGER,
                output TEXT,
                success BOOLEAN NOT NULL
            )
        """)
        
        # Create indexes
        self._create_indexes()
    
    def _create_indexes(self) -> None:
        """Create database indexes for performance"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_node_status_timestamp ON node_status(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_node_status_cluster_node ON node_status(cluster, node_name)",
            "CREATE INDEX IF NOT EXISTS idx_node_events_timestamp ON node_events(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_node_events_cluster_node ON node_events(cluster, node_name)",
            "CREATE INDEX IF NOT EXISTS idx_node_events_severity ON node_events(severity)",
            "CREATE INDEX IF NOT EXISTS idx_recovery_timestamp ON recovery_attempts(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_recovery_cluster_node ON recovery_attempts(cluster, node_name)",
        ]
        
        for index_sql in indexes:
            self.db.execute(index_sql)
    
    def log_node_status(self, cluster: str, node_name: str, status: str,
                       slurm_state: str, is_available: bool, checked_from: str) -> int:
        """
        Log node status check
        
        Args:
            cluster: Cluster name
            node_name: Node name
            status: Status string ('ok' or 'problem')
            slurm_state: SLURM state string
            is_available: Whether node is available
            checked_from: Hostname that performed check
            
        Returns:
            Row ID of inserted record
        """
        timestamp = datetime.datetime.now().isoformat()
        
        result = self.db.execute("""
            INSERT INTO node_status 
            (timestamp, cluster, node_name, status, slurm_state, is_available, checked_from)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (timestamp, cluster, node_name, status, slurm_state, is_available, checked_from))
        
        return result.lastrowid
    
    def log_node_status_batch(self, cluster: str, node_statuses: Dict[str, Dict],
                              checked_from: str) -> int:
        """
        Log multiple node statuses at once
        
        Args:
            cluster: Cluster name
            node_statuses: Dictionary mapping node names to status info
            checked_from: Hostname that performed check
            
        Returns:
            Number of records inserted
        """
        timestamp = datetime.datetime.now().isoformat()
        count = 0
        
        for node_name, status_info in node_statuses.items():
            self.db.execute("""
                INSERT INTO node_status 
                (timestamp, cluster, node_name, status, slurm_state, is_available, checked_from)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp,
                cluster,
                node_name,
                'ok' if status_info['is_available'] else 'problem',
                status_info['slurm_state'],
                status_info['is_available'],
                checked_from
            ))
            count += 1
        
        return count
    
    def log_event(self, cluster: str, node_name: str, event_type: str,
                  details: str, severity: str = 'info') -> int:
        """
        Log a node event
        
        Args:
            cluster: Cluster name
            node_name: Node name
            event_type: Type of event
            details: Event details
            severity: Severity level
            
        Returns:
            Row ID of inserted record
        """
        timestamp = datetime.datetime.now().isoformat()
        
        result = self.db.execute("""
            INSERT INTO node_events 
            (timestamp, cluster, node_name, event_type, details, severity)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (timestamp, cluster, node_name, event_type, details, severity))
        
        return result.lastrowid
    
    def log_recovery_attempt(self, cluster: str, node_name: str, command: str,
                           exit_code: Optional[int], output: str, success: bool) -> int:
        """
        Log a recovery attempt
        
        Args:
            cluster: Cluster name
            node_name: Node name
            command: Command executed
            exit_code: Exit code of command
            output: Command output
            success: Whether recovery was successful
            
        Returns:
            Row ID of inserted record
        """
        timestamp = datetime.datetime.now().isoformat()
        
        result = self.db.execute("""
            INSERT INTO recovery_attempts 
            (timestamp, cluster, node_name, command, exit_code, output, success)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (timestamp, cluster, node_name, command, exit_code, output, success))
        
        return result.lastrowid
    
    def get_latest_status(self, cluster: Optional[str] = None) -> List[tuple]:
        """
        Get latest status for all nodes
        
        Args:
            cluster: Optional cluster filter
            
        Returns:
            List of tuples: (cluster, node_name, slurm_state, is_available, timestamp)
        """
        if cluster:
            query = """
                SELECT cluster, node_name, slurm_state, is_available, timestamp
                FROM node_status
                WHERE timestamp = (SELECT MAX(timestamp) FROM node_status)
                AND cluster = ?
                ORDER BY cluster, node_name
            """
            return self.db.execute(query, (cluster,)).fetchall()
        else:
            query = """
                SELECT cluster, node_name, slurm_state, is_available, timestamp
                FROM node_status
                WHERE timestamp = (SELECT MAX(timestamp) FROM node_status)
                ORDER BY cluster, node_name
            """
            return self.db.execute(query).fetchall()
    
    def get_problem_nodes(self, cluster: Optional[str] = None) -> List[tuple]:
        """
        Get currently problematic nodes
        
        Args:
            cluster: Optional cluster filter
            
        Returns:
            List of tuples: (cluster, node_name, slurm_state, timestamp)
        """
        if cluster:
            query = """
                SELECT cluster, node_name, slurm_state, timestamp
                FROM node_status
                WHERE timestamp = (SELECT MAX(timestamp) FROM node_status)
                AND is_available = 0
                AND cluster = ?
                ORDER BY cluster, node_name
            """
            return self.db.execute(query, (cluster,)).fetchall()
        else:
            query = """
                SELECT cluster, node_name, slurm_state, timestamp
                FROM node_status
                WHERE timestamp = (SELECT MAX(timestamp) FROM node_status)
                AND is_available = 0
                ORDER BY cluster, node_name
            """
            return self.db.execute(query).fetchall()
    
    def get_events(self, cluster: Optional[str] = None, node_name: Optional[str] = None,
                   days: int = 7, severity: Optional[str] = None) -> List[tuple]:
        """
        Get events with optional filters
        
        Args:
            cluster: Optional cluster filter
            node_name: Optional node filter
            days: Number of days to look back
            severity: Optional severity filter
            
        Returns:
            List of event tuples
        """
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
        
        conditions = ["timestamp > ?"]
        params = [cutoff]
        
        if cluster:
            conditions.append("cluster = ?")
            params.append(cluster)
        
        if node_name:
            conditions.append("node_name = ?")
            params.append(node_name)
        
        if severity:
            conditions.append("severity = ?")
            params.append(severity)
        
        query = f"""
            SELECT timestamp, cluster, node_name, event_type, details, severity
            FROM node_events
            WHERE {' AND '.join(conditions)}
            ORDER BY timestamp DESC
        """
        
        return self.db.execute(query, tuple(params)).fetchall()
    
    def get_problem_history(self, days: int = 7, cluster: Optional[str] = None) -> List[tuple]:
        """
        Get problem history statistics
        
        Args:
            days: Number of days to look back
            cluster: Optional cluster filter
            
        Returns:
            List of tuples: (cluster, node_name, count, first_seen, last_seen)
        """
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
        
        if cluster:
            query = """
                SELECT cluster, node_name, COUNT(*) as problem_count,
                       MIN(timestamp) as first_seen,
                       MAX(timestamp) as last_seen
                FROM node_events
                WHERE timestamp > ? 
                AND severity IN ('warning', 'error', 'critical')
                AND event_type = 'node_down'
                AND cluster = ?
                GROUP BY cluster, node_name
                ORDER BY problem_count DESC, cluster, node_name
            """
            return self.db.execute(query, (cutoff, cluster)).fetchall()
        else:
            query = """
                SELECT cluster, node_name, COUNT(*) as problem_count,
                       MIN(timestamp) as first_seen,
                       MAX(timestamp) as last_seen
                FROM node_events
                WHERE timestamp > ? 
                AND severity IN ('warning', 'error', 'critical')
                AND event_type = 'node_down'
                GROUP BY cluster, node_name
                ORDER BY problem_count DESC, cluster, node_name
            """
            return self.db.execute(query, (cutoff,)).fetchall()
    
    def get_recovery_stats(self, days: int = 7, cluster: Optional[str] = None) -> List[tuple]:
        """
        Get recovery attempt statistics
        
        Args:
            days: Number of days to look back
            cluster: Optional cluster filter
            
        Returns:
            List of tuples: (cluster, node_name, successful, failed)
        """
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
        
        if cluster:
            query = """
                SELECT cluster, node_name,
                       SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                       SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed
                FROM recovery_attempts
                WHERE timestamp > ? AND cluster = ?
                GROUP BY cluster, node_name
                ORDER BY cluster, node_name
            """
            return self.db.execute(query, (cutoff, cluster)).fetchall()
        else:
            query = """
                SELECT cluster, node_name,
                       SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                       SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed
                FROM recovery_attempts
                WHERE timestamp > ?
                GROUP BY cluster, node_name
                ORDER BY cluster, node_name
            """
            return self.db.execute(query, (cutoff,)).fetchall()
    
    def get_downtime_stats(self, days: int = 7, cluster: Optional[str] = None) -> List[tuple]:
        """
        Get downtime statistics
        
        Args:
            days: Number of days to look back
            cluster: Optional cluster filter
            
        Returns:
            List of tuples: (cluster, node_name, total_checks, down_checks)
        """
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
        
        if cluster:
            query = """
                SELECT cluster, node_name,
                       COUNT(*) as total_checks,
                       SUM(CASE WHEN is_available = 0 THEN 1 ELSE 0 END) as down_checks
                FROM node_status
                WHERE timestamp > ? AND cluster = ?
                GROUP BY cluster, node_name
                HAVING down_checks > 0
                ORDER BY down_checks DESC, cluster, node_name
            """
            return self.db.execute(query, (cutoff, cluster)).fetchall()
        else:
            query = """
                SELECT cluster, node_name,
                       COUNT(*) as total_checks,
                       SUM(CASE WHEN is_available = 0 THEN 1 ELSE 0 END) as down_checks
                FROM node_status
                WHERE timestamp > ?
                GROUP BY cluster, node_name
                HAVING down_checks > 0
                ORDER BY down_checks DESC, cluster, node_name
            """
            return self.db.execute(query, (cutoff,)).fetchall()
    
    def get_cluster_summary(self) -> List[tuple]:
        """
        Get overall cluster health summary
        
        Returns:
            List of tuples: (cluster, total_nodes, healthy, problem)
        """
        query = """
            SELECT cluster, 
                   COUNT(*) as total_nodes,
                   SUM(CASE WHEN is_available = 1 THEN 1 ELSE 0 END) as healthy,
                   SUM(CASE WHEN is_available = 0 THEN 1 ELSE 0 END) as problem
            FROM node_status
            WHERE timestamp = (SELECT MAX(timestamp) FROM node_status)
            GROUP BY cluster
        """
        return self.db.execute(query).fetchall()
    
    def cleanup_old_records(self, days: int = 90) -> Dict[str, int]:
        """
        Delete records older than specified days
        
        Args:
            days: Records older than this are deleted
            
        Returns:
            Dictionary with count of deleted records per table
        """
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
        
        deleted = {}
        
        # Delete old node_status records
        result = self.db.execute("DELETE FROM node_status WHERE timestamp < ?", (cutoff,))
        deleted['node_status'] = result.rowcount
        
        # Delete old node_events records
        result = self.db.execute("DELETE FROM node_events WHERE timestamp < ?", (cutoff,))
        deleted['node_events'] = result.rowcount
        
        # Delete old recovery_attempts records
        result = self.db.execute("DELETE FROM recovery_attempts WHERE timestamp < ?", (cutoff,))
        deleted['recovery_attempts'] = result.rowcount
        
        # Vacuum to reclaim space
        self.db.execute("VACUUM")
        
        return deleted
    
    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get database statistics
        
        Returns:
            Dictionary with database statistics
        """
        stats = {}
        
        # Record counts
        stats['node_status_count'] = self.db.execute(
            "SELECT COUNT(*) FROM node_status"
        ).fetchone()[0]
        
        stats['node_events_count'] = self.db.execute(
            "SELECT COUNT(*) FROM node_events"
        ).fetchone()[0]
        
        stats['recovery_attempts_count'] = self.db.execute(
            "SELECT COUNT(*) FROM recovery_attempts"
        ).fetchone()[0]
        
        # Date range
        oldest = self.db.execute(
            "SELECT MIN(timestamp) FROM node_status"
        ).fetchone()[0]
        
        newest = self.db.execute(
            "SELECT MAX(timestamp) FROM node_status"
        ).fetchone()[0]
        
        stats['oldest_record'] = oldest
        stats['newest_record'] = newest
        
        # Database file size
        if self.db_path.exists():
            stats['db_size_bytes'] = self.db_path.stat().st_size
            stats['db_size_mb'] = stats['db_size_bytes'] / (1024 * 1024)
        
        return stats
