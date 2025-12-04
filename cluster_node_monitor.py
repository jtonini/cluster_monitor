#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cluster Node Monitor
Monitors nodes on spydur and arachne clusters, detects failures, 
attempts recovery, and logs all events to database.

Clusters:
- spydur: 30 nodes (spdr01-18, spdr50-61), management user 'installer'
- arachne: 6 nodes (node01-03, node51-53), management user 'zeus'

Runs from: badenpowell as user 'cazuza'
"""
import typing
from typing import *

min_py = (3, 8)

###
# Standard imports, starting with os and sys
###
import os
import sys
if sys.version_info < min_py:
    print(f"This program requires Python {min_py[0]}.{min_py[1]}, or higher.")
    sys.exit(os.EX_SOFTWARE)

###
# Other standard distro imports
###
import argparse
import contextlib
import datetime
import json
import logging
import signal
import socket
import time
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

###
# Installed libraries
###
try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # Python 3.6-3.10
    except ImportError:
        print("ERROR: Neither tomllib nor tomli available. Install tomli: pip install tomli")
        sys.exit(os.EX_SOFTWARE)

###
# From hpclib (included in repo)
###
from urdb import URdb
from dorunrun import dorunrun
import fname

###
# Global constants
###
MYNAME = fname.Fname(__file__)
CONFIG_FILE = Path.home() / ".config" / "cluster_monitor" / "config.toml"
DB_PATH = Path.home() / "cluster_monitor.db"
LOG_FILE = Path.home() / "cluster_monitor.log"

###
# Cluster configurations
###
CLUSTERS = {
    'spydur': {
        'user': 'installer',
        'head_node': 'spydur',
        'nodes': [f'spdr{i:02d}' for i in range(1, 19)] + [f'spdr{i}' for i in range(50, 62)],
        'check_command': 'sinfo -h -N -o "%N %T"',  # Node name and state
        'recovery_commands': [
            'sudo -u slurm scontrol update nodename={node} state=resume',
            'ssh {node} "sudo systemctl restart slurmd"'
        ],
        'problem_states': ['down', 'drain', 'drng', 'fail', 'failing', 'maint', 'unk', 'unknown']
    },
    'arachne': {
        'user': 'zeus',
        'head_node': 'arachne',
        'nodes': [f'node{i:02d}' for i in range(1, 4)] + [f'node{i}' for i in range(51, 54)],
        'check_command': 'sinfo -h -N -o "%N %T"',
        'recovery_commands': [
            'sudo scontrol update nodename={node} state=resume',
            'ssh {node} "systemctl restart slurmd"'
        ],
        'problem_states': ['down', 'drain', 'drng', 'fail', 'failing', 'maint', 'unk', 'unknown']
    }
}


class ClusterNodeMonitor:
    """Monitor and manage cluster nodes across multiple clusters"""
    
    def __init__(self, config_file: Path = CONFIG_FILE, db_path: Path = DB_PATH):
        """
        Initialize the cluster node monitor
        
        Args:
            config_file: Path to TOML configuration file
            db_path: Path to SQLite database
        """
        self.config_file = config_file
        self.db_path = db_path
        self.control_host = socket.gethostname()  # Should be 'badenpowell'
        self.clusters = CLUSTERS.copy()
        
        # Email configuration (will be overridden by config file)
        self.email_config = {
            'enabled': True,
            'from': f'cazuza@{self.control_host}',
            'to': ['cazuza@badenpowell'],  # Update in config.toml
            'smtp_server': 'localhost',
            'smtp_port': 25
        }
        
        # Setup logging
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(LOG_FILE),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('ClusterMonitor')
        
        # Load configuration
        self.load_config()
        
        # Initialize database
        self.init_database()
    
    def load_config(self) -> None:
        """Load configuration from TOML file"""
        if not self.config_file.exists():
            self.logger.warning(f"Config file not found: {self.config_file}")
            self.logger.info("Using default configuration")
            self.create_default_config()
            return
        
        try:
            with open(self.config_file, 'rb') as f:
                config = tomllib.load(f)
            
            # Update cluster configurations
            for cluster_name in ['spydur', 'arachne']:
                if cluster_name in config:
                    self.clusters[cluster_name].update(config[cluster_name])
            
            # Update email settings if present
            if 'email' in config:
                self.email_config.update(config['email'])
            
            self.logger.info(f"Configuration loaded from {self.config_file}")
        
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            self.logger.info("Using default configuration")
    
    def create_default_config(self) -> None:
        """Create a default configuration file"""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        config_content = """# Cluster Node Monitor Configuration

[email]
enabled = true
from = "cazuza@badenpowell"
to = ["your-email@domain.com"]
smtp_server = "localhost"
smtp_port = 25

[spydur]
user = "installer"
head_node = "spydur"
# Nodes are auto-populated, but you can override here if needed
# nodes = ["spdr01", "spdr02", ...]

[arachne]
user = "zeus"
head_node = "arachne"
# Nodes are auto-populated, but you can override here if needed
# nodes = ["node01", "node02", ...]

[monitoring]
# How often to check (in seconds) - set via cron, this is just for reference
check_interval = 300  # 5 minutes

# How many recovery attempts before giving up
max_recovery_attempts = 3

# Wait time between recovery attempts (seconds)
recovery_wait_time = 60
"""
        
        try:
            with open(self.config_file, 'w') as f:
                f.write(config_content)
            self.logger.info(f"Default configuration created at {self.config_file}")
            self.logger.info("Please edit the configuration file and update email settings")
        except Exception as e:
            self.logger.error(f"Error creating default config: {e}")
    
    def init_database(self) -> None:
        """Initialize SQLite database with required tables"""
        try:
            db = URdb(str(self.db_path))
            
            # Node status table
            db.execute("""
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
            
            # Node events table (for tracking issues and recovery)
            db.execute("""
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
            db.execute("""
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
            
            # Create indexes for better query performance
            db.execute("""
                CREATE INDEX IF NOT EXISTS idx_node_status_timestamp 
                ON node_status(timestamp)
            """)
            
            db.execute("""
                CREATE INDEX IF NOT EXISTS idx_node_events_timestamp 
                ON node_events(timestamp)
            """)
            
            db.execute("""
                CREATE INDEX IF NOT EXISTS idx_node_events_cluster_node 
                ON node_events(cluster, node_name)
            """)
            
            self.logger.info(f"Database initialized at {self.db_path}")
        
        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
            raise
    
    def check_cluster(self, cluster_name: str) -> Dict[str, Dict]:
        """
        Check all nodes in a cluster using SLURM sinfo
        
        Args:
            cluster_name: Name of cluster ('spydur' or 'arachne')
            
        Returns:
            Dictionary mapping node names to their status info
        """
        cluster = self.clusters[cluster_name]
        self.logger.info(f"Checking cluster: {cluster_name}")
        
        # Build SSH command to run sinfo on the cluster
        ssh_cmd = f"ssh {cluster['user']}@{cluster['head_node']} '{cluster['check_command']}'"
        
        # Execute command using dorunrun
        result = dorunrun(ssh_cmd, return_datatype=str)
        
        node_statuses = {}
        
        if result.OK:
            # Parse sinfo output
            lines = result.value.strip().split('\n')
            for line in lines:
                if not line.strip():
                    continue
                
                parts = line.split()
                if len(parts) >= 2:
                    node_name = parts[0]
                    slurm_state = parts[1].lower()
                    
                    # Determine if node is in problem state
                    is_problem = any(prob_state in slurm_state for prob_state in cluster['problem_states'])
                    
                    node_statuses[node_name] = {
                        'slurm_state': slurm_state,
                        'is_available': not is_problem,
                        'raw_line': line
                    }
        else:
            self.logger.error(f"Failed to check {cluster_name}: {result.stderr}")
            # Log the error event
            self.log_event(
                cluster_name,
                cluster['head_node'],
                'check_failed',
                f"Failed to run sinfo: {result.stderr}",
                'error'
            )
        
        return node_statuses
    
    def log_status(self, cluster_name: str, node_statuses: Dict[str, Dict]) -> None:
        """
        Log node statuses to database
        
        Args:
            cluster_name: Name of cluster
            node_statuses: Dictionary of node statuses
        """
        timestamp = datetime.datetime.now().isoformat()
        db = URdb(str(self.db_path))
        
        for node_name, status_info in node_statuses.items():
            db.execute("""
                INSERT INTO node_status 
                (timestamp, cluster, node_name, status, slurm_state, is_available, checked_from)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp,
                cluster_name,
                node_name,
                'ok' if status_info['is_available'] else 'problem',
                status_info['slurm_state'],
                status_info['is_available'],
                self.control_host
            ))
    
    def log_event(self, cluster_name: str, node_name: str, event_type: str, 
                  details: str, severity: str = 'info') -> None:
        """
        Log a node event to database
        
        Args:
            cluster_name: Name of cluster
            node_name: Name of node
            event_type: Type of event (e.g., 'down_detected', 'recovery_attempted')
            details: Event details
            severity: Severity level ('info', 'warning', 'error', 'critical')
        """
        timestamp = datetime.datetime.now().isoformat()
        db = URdb(str(self.db_path))
        
        db.execute("""
            INSERT INTO node_events 
            (timestamp, cluster, node_name, event_type, details, severity)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (timestamp, cluster_name, node_name, event_type, details, severity))
    
    def log_recovery_attempt(self, cluster_name: str, node_name: str, 
                           command: str, result) -> None:
        """
        Log a recovery attempt to database
        
        Args:
            cluster_name: Name of cluster
            node_name: Name of node
            command: Command that was executed
            result: Result from dorunrun
        """
        timestamp = datetime.datetime.now().isoformat()
        db = URdb(str(self.db_path))
        
        db.execute("""
            INSERT INTO recovery_attempts 
            (timestamp, cluster, node_name, command, exit_code, output, success)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            timestamp,
            cluster_name,
            node_name,
            command,
            result.exit_code if hasattr(result, 'exit_code') else None,
            result.stdout if hasattr(result, 'stdout') else str(result),
            result.OK
        ))
    
    def attempt_recovery(self, cluster_name: str, node_name: str) -> bool:
        """
        Attempt to recover a problematic node
        
        Args:
            cluster_name: Name of cluster
            node_name: Name of node
            
        Returns:
            True if recovery was successful, False otherwise
        """
        cluster = self.clusters[cluster_name]
        self.logger.info(f"Attempting recovery for {cluster_name}:{node_name}")
        
        # Log the recovery attempt event
        self.log_event(
            cluster_name,
            node_name,
            'recovery_started',
            f"Starting recovery procedures",
            'warning'
        )
        
        # Try each recovery command in sequence
        for cmd_template in cluster['recovery_commands']:
            # Format command with node name
            command = cmd_template.format(node=node_name)
            
            # Build full SSH command
            if command.startswith('ssh'):
                # Command already has SSH
                full_cmd = f"ssh {cluster['user']}@{cluster['head_node']} \"{command.replace('ssh ' + node_name, '')}\""
            else:
                # Add SSH wrapper
                full_cmd = f"ssh {cluster['user']}@{cluster['head_node']} '{command}'"
            
            self.logger.info(f"Executing recovery command: {full_cmd}")
            
            # Execute recovery command
            result = dorunrun(full_cmd, return_datatype=str)
            
            # Log the attempt
            self.log_recovery_attempt(cluster_name, node_name, full_cmd, result)
            
            if result.OK:
                self.logger.info(f"Recovery command succeeded: {command}")
                
                # Wait a bit for node to come back
                time.sleep(10)
                
                # Check if node is back
                node_statuses = self.check_cluster(cluster_name)
                if node_name in node_statuses and node_statuses[node_name]['is_available']:
                    self.logger.info(f"Node {cluster_name}:{node_name} successfully recovered!")
                    self.log_event(
                        cluster_name,
                        node_name,
                        'recovery_successful',
                        f"Node recovered using: {command}",
                        'info'
                    )
                    return True
            else:
                self.logger.warning(f"Recovery command failed: {command}")
                self.logger.warning(f"Error: {result.stderr}")
        
        # All recovery attempts failed
        self.log_event(
            cluster_name,
            node_name,
            'recovery_failed',
            f"All recovery attempts failed",
            'critical'
        )
        return False
    
    def send_notification(self, subject: str, body: str, severity: str = 'info') -> None:
        """
        Send email notification
        
        Args:
            subject: Email subject
            body: Email body
            severity: Message severity
        """
        if not self.email_config['enabled']:
            self.logger.info("Email notifications disabled")
            return
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_config['from']
            msg['To'] = ', '.join(self.email_config['to'])
            msg['Subject'] = f"[{severity.upper()}] {subject}"
            
            # Add timestamp and hostname to body
            full_body = f"""
Cluster Node Monitor Alert
==========================

Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Host: {self.control_host}
Severity: {severity.upper()}

{body}

---
This is an automated message from the Cluster Node Monitor
Running on {self.control_host} as {os.getenv('USER', 'unknown')}
"""
            
            msg.attach(MIMEText(full_body, 'plain'))
            
            # Send email
            with smtplib.SMTP(self.email_config['smtp_server'], 
                            self.email_config['smtp_port']) as server:
                server.send_message(msg)
            
            self.logger.info(f"Notification sent: {subject}")
        
        except Exception as e:
            self.logger.error(f"Failed to send notification: {e}")
    
    def monitor_all_clusters(self, attempt_recovery: bool = True) -> Dict[str, Any]:
        """
        Monitor all configured clusters
        
        Args:
            attempt_recovery: Whether to attempt recovery for problematic nodes
            
        Returns:
            Summary of monitoring run
        """
        summary = {
            'timestamp': datetime.datetime.now().isoformat(),
            'clusters': {},
            'total_nodes': 0,
            'healthy_nodes': 0,
            'problem_nodes': 0,
            'recovered_nodes': 0,
            'failed_recovery': 0
        }
        
        for cluster_name in ['spydur', 'arachne']:
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"Monitoring cluster: {cluster_name}")
            self.logger.info(f"{'='*60}")
            
            # Check cluster
            node_statuses = self.check_cluster(cluster_name)
            
            if not node_statuses:
                self.logger.error(f"No node status data for {cluster_name}")
                continue
            
            # Log statuses to database
            self.log_status(cluster_name, node_statuses)
            
            # Analyze results
            problem_nodes = []
            healthy_nodes = []
            
            for node_name, status_info in node_statuses.items():
                summary['total_nodes'] += 1
                
                if status_info['is_available']:
                    healthy_nodes.append(node_name)
                    summary['healthy_nodes'] += 1
                else:
                    problem_nodes.append(node_name)
                    summary['problem_nodes'] += 1
                    
                    # Log the problem
                    self.log_event(
                        cluster_name,
                        node_name,
                        'node_down',
                        f"Node in problematic state: {status_info['slurm_state']}",
                        'warning'
                    )
            
            # Store cluster summary
            summary['clusters'][cluster_name] = {
                'total': len(node_statuses),
                'healthy': len(healthy_nodes),
                'problem': len(problem_nodes),
                'problem_nodes': problem_nodes
            }
            
            self.logger.info(f"Cluster {cluster_name} summary:")
            self.logger.info(f"  Total nodes: {len(node_statuses)}")
            self.logger.info(f"  Healthy: {len(healthy_nodes)}")
            self.logger.info(f"  Problems: {len(problem_nodes)}")
            
            if problem_nodes:
                self.logger.warning(f"  Problem nodes: {', '.join(problem_nodes)}")
                
                # Attempt recovery if enabled
                if attempt_recovery:
                    for node_name in problem_nodes:
                        self.logger.info(f"\nAttempting recovery for {node_name}...")
                        if self.attempt_recovery(cluster_name, node_name):
                            summary['recovered_nodes'] += 1
                        else:
                            summary['failed_recovery'] += 1
                
                # Send notification for problem nodes
                self.send_notification(
                    f"Cluster {cluster_name}: {len(problem_nodes)} node(s) down",
                    f"""Problem nodes detected on {cluster_name}:

{chr(10).join([f"  - {node}: {node_statuses[node]['slurm_state']}" for node in problem_nodes])}

Recovery attempted: {attempt_recovery}
Recovered: {summary['recovered_nodes']}
Failed: {summary['failed_recovery']}
""",
                    severity='critical' if len(problem_nodes) > 3 else 'warning'
                )
        
        return summary
    
    def generate_status_report(self, days: int = 7) -> str:
        """
        Generate a status report for the last N days
        
        Args:
            days: Number of days to include in report
            
        Returns:
            Formatted report string
        """
        db = URdb(str(self.db_path))
        
        cutoff_date = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
        
        # Get node events
        events = db.execute("""
            SELECT cluster, node_name, event_type, COUNT(*) as count
            FROM node_events
            WHERE timestamp > ? AND severity IN ('warning', 'error', 'critical')
            GROUP BY cluster, node_name, event_type
            ORDER BY count DESC
        """, (cutoff_date,)).fetchall()
        
        # Get recovery stats
        recovery_stats = db.execute("""
            SELECT cluster, success, COUNT(*) as count
            FROM recovery_attempts
            WHERE timestamp > ?
            GROUP BY cluster, success
        """, (cutoff_date,)).fetchall()
        
        # Build report
        report = f"""
CLUSTER NODE MONITOR - STATUS REPORT
=====================================
Period: Last {days} days
Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

NODE EVENTS SUMMARY
-------------------
"""
        
        if events:
            for event in events:
                report += f"{event[0]:10} {event[1]:15} {event[2]:20} {event[3]:5} times\n"
        else:
            report += "No events recorded\n"
        
        report += "\nRECOVERY ATTEMPTS\n-----------------\n"
        
        if recovery_stats:
            for stat in recovery_stats:
                status = "Success" if stat[1] else "Failed"
                report += f"{stat[0]:10} {status:10} {stat[2]:5} attempts\n"
        else:
            report += "No recovery attempts\n"
        
        return report


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Monitor cluster nodes and attempt recovery',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Monitor all clusters and attempt recovery
  %(prog)s --monitor

  # Monitor without recovery attempts
  %(prog)s --monitor --no-recovery

  # Generate status report
  %(prog)s --report

  # Generate 30-day report
  %(prog)s --report --days 30

  # Check specific cluster
  %(prog)s --cluster spydur --monitor
        """
    )
    
    parser.add_argument('--monitor', action='store_true',
                       help='Monitor all clusters')
    
    parser.add_argument('--cluster', choices=['spydur', 'arachne'],
                       help='Monitor specific cluster only')
    
    parser.add_argument('--no-recovery', action='store_true',
                       help='Check status only, do not attempt recovery')
    
    parser.add_argument('--report', action='store_true',
                       help='Generate status report')
    
    parser.add_argument('--days', type=int, default=7,
                       help='Number of days for report (default: 7)')
    
    parser.add_argument('--config', type=Path, default=CONFIG_FILE,
                       help=f'Configuration file (default: {CONFIG_FILE})')
    
    parser.add_argument('--db', type=Path, default=DB_PATH,
                       help=f'Database file (default: {DB_PATH})')
    
    args = parser.parse_args()
    
    # Create monitor instance
    monitor = ClusterNodeMonitor(config_file=args.config, db_path=args.db)
    
    try:
        if args.report:
            # Generate report
            report = monitor.generate_status_report(days=args.days)
            print(report)
        
        elif args.monitor:
            # Monitor clusters
            summary = monitor.monitor_all_clusters(
                attempt_recovery=not args.no_recovery
            )
            
            # Print summary
            print("\n" + "="*60)
            print("MONITORING SUMMARY")
            print("="*60)
            print(f"Total nodes checked: {summary['total_nodes']}")
            print(f"Healthy nodes: {summary['healthy_nodes']}")
            print(f"Problem nodes: {summary['problem_nodes']}")
            if not args.no_recovery:
                print(f"Recovered nodes: {summary['recovered_nodes']}")
                print(f"Failed recovery: {summary['failed_recovery']}")
            print("="*60)
        
        else:
            parser.print_help()
            return os.EX_USAGE
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return os.EX_OK
    
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return os.EX_SOFTWARE
    
    return os.EX_OK


if __name__ == '__main__':
    sys.exit(main())
