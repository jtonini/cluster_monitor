#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check Queue - Quick queue analysis tool
"""
import typing
from typing import *

min_py = (3, 8)

import os
import sys
if sys.version_info < min_py:
    print(f"This program requires Python {min_py[0]}.{min_py[1]}, or higher.")
    sys.exit(os.EX_SOFTWARE)

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from pathlib import Path
from job_queue_analyzer import JobQueueAnalyzer


def load_config() -> dict:
    """Load cluster configuration"""
    config_path = Path.home() / '.config' / 'cluster_monitor' / 'config.toml'
    
    if not config_path.exists():
        print(f"Configuration not found: {config_path}")
        print("Run cluster_node_monitor.py first to create configuration")
        sys.exit(1)
    
    with open(config_path, 'rb') as f:
        return tomllib.load(f)


def get_clusters(config: dict) -> List[str]:
    """Get list of cluster names from config"""
    clusters = []
    for section_name, section_data in config.items():
        # A cluster section must have 'user' and 'head_node' keys
        if isinstance(section_data, dict):
            if 'user' in section_data and 'head_node' in section_data:
                clusters.append(section_name)
    return clusters


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Check SLURM queue for misleading job status messages'
    )
    parser.add_argument('--cluster', help='Check specific cluster only')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show all jobs, not just misleading ones')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    
    # Determine which clusters to check
    if args.cluster:
        if args.cluster not in config:
            print(f"Cluster '{args.cluster}' not found in configuration")
            return 1
        clusters_to_check = [args.cluster]
    else:
        # Get all valid cluster configurations
        clusters_to_check = get_clusters(config)
    
    if not clusters_to_check:
        print("No cluster configurations found")
        return 1
    
    print("="*60)
    print("SLURM QUEUE ANALYSIS")
    print("="*60)
    print()
    
    total_misleading = 0
    
    for cluster_name in clusters_to_check:
        cluster_config = config[cluster_name]
        
        print(f"Checking {cluster_name}...")
        
        analyzer = JobQueueAnalyzer(
            cluster=cluster_name,
            user=cluster_config['user'],
            head_node=cluster_config['head_node']
        )
        
        try:
            results = analyzer.analyze_queue()
            
            if results:
                print(f"\nFound {len(results)} misleading status messages:\n")
                total_misleading += len(results)
                
                for result in results:
                    job = result['job']
                    print(f"  Job {job['jobid']} - {job['name']} ({job['user']})")
                    print(f"    Status says: {job['reason']}")
                    print(f"    Reality: {result['real_reason']}")
                    
                    if args.verbose:
                        for detail in result['details']:
                            print(f"      {detail}")
                    print()
            else:
                print("  No misleading statuses found")
                print()
        
        except Exception as e:
            print(f"  Error analyzing queue: {e}")
            print()
    
    print("="*60)
    print(f"Total misleading job statuses: {total_misleading}")
    print("="*60)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
