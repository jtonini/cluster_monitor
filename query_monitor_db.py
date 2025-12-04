#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cluster Monitor Database Query Tool
Query and analyze cluster monitoring data
"""
import typing
from typing import *

min_py = (3, 8)

import os
import sys
if sys.version_info < min_py:
    print(f"This program requires Python {min_py[0]}.{min_py[1]}, or higher.")
    sys.exit(os.EX_SOFTWARE)

import argparse
import datetime
from pathlib import Path

# Import database wrapper
from urdb import URdb


class ClusterMonitorQuery:
    """Query cluster monitoring database"""
    
    def __init__(self, db_path: Path):
        """Initialize query tool"""
        self.db_path = db_path
        if not db_path.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")
        self.db = URdb(str(db_path))
    
    def list_nodes(self):
        """List all monitored nodes by cluster"""
        result = self.db.execute("""
            SELECT DISTINCT cluster, node_name 
            FROM node_status 
            ORDER BY cluster, node_name
        """).fetchall()
        
        print("\n" + "="*60)
        print("NODES BY CLUSTER")
        print("="*60)
        
        current_cluster = None
        for row in result:
            cluster, node = row
            if cluster != current_cluster:
                print(f"{cluster}:")
                current_cluster = cluster
            print(f"  - {node}")
    
    def current_status(self, cluster: Optional[str] = None):
        """Show current status of all nodes"""
        # Fixed query: get max timestamp PER CLUSTER
        if cluster:
            query = """
                SELECT ns1.cluster, ns1.node_name, ns1.slurm_state, ns1.is_available, ns1.timestamp
                FROM node_status ns1
                INNER JOIN (
                    SELECT cluster, MAX(timestamp) as max_ts
                    FROM node_status
                    WHERE cluster = ?
                    GROUP BY cluster
                ) ns2 ON ns1.cluster = ns2.cluster AND ns1.timestamp = ns2.max_ts
                ORDER BY ns1.cluster, ns1.node_name
            """
            result = self.db.execute(query, (cluster,)).fetchall()
        else:
            query = """
                SELECT ns1.cluster, ns1.node_name, ns1.slurm_state, ns1.is_available, ns1.timestamp
                FROM node_status ns1
                INNER JOIN (
                    SELECT cluster, MAX(timestamp) as max_ts
                    FROM node_status
                    GROUP BY cluster
                ) ns2 ON ns1.cluster = ns2.cluster AND ns1.timestamp = ns2.max_ts
                ORDER BY ns1.cluster, ns1.node_name
            """
            result = self.db.execute(query).fetchall()
        
        print("\n" + "="*60)
        print("CURRENT NODE STATUS")
        print("="*60)
        
        current_cluster = None
        cluster_stats = {}
        
        for row in result:
            cluster_name, node, state, is_available, timestamp = row
            
            if cluster_name != current_cluster:
                if current_cluster:
                    stats = cluster_stats[current_cluster]
                    print(f"  Summary: {stats['healthy']} healthy, {stats['problem']} problem")
                    print()
                
                print(f"{cluster_name} (as of {timestamp}):")
                current_cluster = cluster_name
                cluster_stats[cluster_name] = {'healthy': 0, 'problem': 0}
            
            status_mark = "[OK]" if is_available else "[X]"
            print(f"  {status_mark} {node:12s}  {state}")
            
            if is_available:
                cluster_stats[cluster_name]['healthy'] += 1
            else:
                cluster_stats[cluster_name]['problem'] += 1
        
        if current_cluster:
            stats = cluster_stats[current_cluster]
            print(f"  Summary: {stats['healthy']} healthy, {stats['problem']} problem")
    
    def problem_history(self, days: int = 7, cluster: Optional[str] = None):
        """Show problem history"""
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
        
        if cluster:
            where = "AND cluster = ?"
            params = (cutoff, cluster)
        else:
            where = ""
            params = (cutoff,)
        
        result = self.db.execute(f"""
            SELECT timestamp, cluster, node_name, event_type, details, severity
            FROM node_events
            WHERE timestamp > ? {where}
            AND severity IN ('warning', 'error', 'critical')
            ORDER BY timestamp DESC
        """, params).fetchall()
        
        print("\n" + "="*60)
        print(f"PROBLEM HISTORY - Last {days} days")
        print("="*60)
        
        if not result:
            print("No problems detected!")
            return
        
        for row in result:
            timestamp, cluster, node, event_type, details, severity = row
            print(f"\n{timestamp} [{severity.upper()}]")
            print(f"  Cluster: {cluster}")
            print(f"  Node: {node}")
            print(f"  Event: {event_type}")
            print(f"  Details: {details}")
    
    def recovery_stats(self, days: int = 7):
        """Show recovery attempt statistics"""
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
        
        result = self.db.execute("""
            SELECT cluster, node_name, recovery_action, success, 
                   COUNT(*) as attempts,
                   SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful
            FROM recovery_attempts
            WHERE timestamp > ?
            GROUP BY cluster, node_name, recovery_action, success
            ORDER BY cluster, node_name, timestamp DESC
        """, (cutoff,)).fetchall()
        
        print("\n" + "="*60)
        print(f"RECOVERY STATISTICS - Last {days} days")
        print("="*60)
        
        if not result:
            print("No recovery attempts in this period")
            return
        
        current_cluster = None
        for row in result:
            cluster, node, action, success, attempts, successful = row
            
            if cluster != current_cluster:
                if current_cluster:
                    print()
                print(f"\n{cluster}:")
                current_cluster = cluster
            
            status = "SUCCESS" if success else "FAILED"
            print(f"  {node}: {action} - {status} ({successful}/{attempts} attempts)")
    
    def downtime_report(self, days: int = 7):
        """Show downtime statistics"""
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
        
        result = self.db.execute("""
            SELECT cluster, node_name,
                   COUNT(*) as checks,
                   SUM(CASE WHEN is_available = 0 THEN 1 ELSE 0 END) as down_checks
            FROM node_status
            WHERE timestamp > ?
            GROUP BY cluster, node_name
            HAVING down_checks > 0
            ORDER BY cluster, down_checks DESC
        """, (cutoff,)).fetchall()
        
        print("\n" + "="*60)
        print(f"DOWNTIME REPORT - Last {days} days")
        print("="*60)
        print("Note: Downtime % is approximate based on monitoring frequency")
        print("-"*60)
        
        if not result:
            print("No downtime detected!")
            return
        
        current_cluster = None
        for row in result:
            cluster, node, checks, down_checks = row
            downtime_pct = (down_checks / checks) * 100
            
            if cluster != current_cluster:
                if current_cluster:
                    print()
                print(f"\n{cluster}:")
                current_cluster = cluster
            
            print(f"  {node}: {down_checks}/{checks} checks down ({downtime_pct:.1f}%)")
    
    
    def node_detail(self, cluster: str, node: str, days: int = 7):
        """Show detailed information for a specific node"""
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
        
        print("\n" + "="*60)
        print(f"NODE DETAIL: {cluster}:{node}")
        print("="*60)
        
        # Recent events
        events = self.db.execute("""
            SELECT timestamp, event_type, details, severity
            FROM node_events
            WHERE cluster = ? AND node_name = ? AND timestamp > ?
            ORDER BY timestamp DESC
        """, (cluster, node, cutoff)).fetchall()
        
        if events:
            print(f"\nRecent events (last {days} days):")
            for timestamp, event_type, details, severity in events:
                print(f"  {timestamp} [{severity}] {event_type}: {details}")
        else:
            print(f"\nNo events in the last {days} days")
        
        # Recovery attempts
        recoveries = self.db.execute("""
            SELECT timestamp, command, success, output
            FROM recovery_attempts
            WHERE cluster = ? AND node_name = ? AND timestamp > ?
            ORDER BY timestamp DESC
        """, (cluster, node, cutoff)).fetchall()
        
        if recoveries:
            print(f"\nRecovery attempts (last {days} days):")
            for timestamp, command, success, output in recoveries:
                status = "SUCCESS" if success else f"FAILED: {output}"
                print(f"  {timestamp} {command}: {status}")
        else:
            print(f"\nNo recovery attempts in the last {days} days")

    def health_summary(self):
        """Show overall health summary"""
        # Get latest status per cluster
        result = self.db.execute("""
            SELECT ns1.cluster,
                   COUNT(*) as total_nodes,
                   SUM(CASE WHEN ns1.is_available = 1 THEN 1 ELSE 0 END) as healthy_nodes,
                   MAX(ns1.timestamp) as last_check
            FROM node_status ns1
            INNER JOIN (
                SELECT cluster, MAX(timestamp) as max_ts
                FROM node_status
                GROUP BY cluster
            ) ns2 ON ns1.cluster = ns2.cluster AND ns1.timestamp = ns2.max_ts
            GROUP BY ns1.cluster
        """).fetchall()
        
        print("\n" + "="*60)
        print("CLUSTER HEALTH SUMMARY")
        print("="*60)
        
        for cluster, total, healthy, last_check in result:
            problem = total - healthy
            health_pct = (healthy / total * 100) if total > 0 else 0
            
            print(f"\n{cluster}:")
            print(f"  Total nodes:    {total}")
            print(f"  Healthy:        {healthy} ({health_pct:.1f}%)")
            print(f"  Problem:        {problem}")
            
            # Get 24h issue count
            cutoff_24h = (datetime.datetime.now() - datetime.timedelta(hours=24)).isoformat()
            issues = self.db.execute("""
                SELECT COUNT(*) FROM node_events
                WHERE cluster = ? AND timestamp > ?
                AND severity IN ('warning', 'error', 'critical')
            """, (cluster, cutoff_24h)).fetchone()[0]
            print(f"  Issues (24h):   {issues}")


def main():
    parser = argparse.ArgumentParser(description='Query cluster monitoring database')
    
    parser.add_argument('--db', type=Path, 
                       default=Path.home() / 'cluster_monitor.db',
                       help='Database file path')
    
    parser.add_argument('--cluster', choices=['spydur', 'arachne'],
                       help='Filter by cluster')
    
    parser.add_argument('--days', type=int, default=7,
                       help='Number of days to query (default: 7)')
    
    # Query types
    parser.add_argument('--list-nodes', action='store_true',
                       help='List all monitored nodes')
    
    parser.add_argument('--current', action='store_true',
                       help='Show current status of all nodes')
    
    parser.add_argument('--problems', action='store_true',
                       help='Show problem history')
    
    parser.add_argument('--recovery-stats', action='store_true',
                       help='Show recovery statistics')
    
    parser.add_argument('--downtime', action='store_true',
                       help='Show downtime report')
    
    parser.add_argument('--node-detail', nargs=2, metavar=('CLUSTER', 'NODE'),
                       help='Show details for specific node')
    
    parser.add_argument('--health', action='store_true',
                       help='Show overall health summary')
    
    args = parser.parse_args()
    
    try:
        query = ClusterMonitorQuery(args.db)
        
        if args.list_nodes:
            query.list_nodes()
        elif args.current:
            query.current_status(args.cluster)
        elif args.problems:
            query.problem_history(args.days, args.cluster)
        elif args.recovery_stats:
            query.recovery_stats(args.days)
        elif args.downtime:
            query.downtime_report(args.days)
        elif args.node_detail:
            cluster, node = args.node_detail
            query.node_detail(cluster, node, args.days)
        elif args.health:
            query.health_summary()
        else:
            parser.print_help()
            return os.EX_USAGE
    
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return os.EX_SOFTWARE
    
    return os.EX_OK


if __name__ == '__main__':
    sys.exit(main())
