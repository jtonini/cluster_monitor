#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Job Queue Analyzer
Detect misleading job status messages in SLURM queue
"""
import typing
from typing import *

min_py = (3, 8)

import os
import sys
if sys.version_info < min_py:
    print(f"This program requires Python {min_py[0]}.{min_py[1]}, or higher.")
    sys.exit(os.EX_SOFTWARE)

import re
import subprocess
from datetime import datetime
from collections import defaultdict


class JobQueueAnalyzer:
    """Analyze SLURM job queue for misleading status messages"""
    
    def __init__(self, cluster: str, user: str, head_node: str):
        """
        Initialize analyzer for a cluster
        
        Args:
            cluster: Cluster name (e.g., 'spydur', 'arachne')
            user: SSH user for cluster access
            head_node: Head node hostname
        """
        self.cluster = cluster
        self.user = user
        self.head_node = head_node
        self.ssh_prefix = f"ssh {user}@{head_node}"
    
    def run_command(self, command: str) -> Tuple[int, str, str]:
        """Run SSH command on cluster"""
        full_cmd = f"{self.ssh_prefix} '{command}'"
        result = subprocess.run(
            full_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode, result.stdout, result.stderr
    
    def get_queue_jobs(self) -> List[Dict[str, str]]:
        """Get all pending jobs with reason codes"""
        # Get pending jobs with detailed reason
        cmd = "squeue -t PD -o '%i|%P|%j|%u|%r|%R' --noheader"
        rc, stdout, stderr = self.run_command(cmd)
        
        if rc != 0:
            return []
        
        jobs = []
        for line in stdout.strip().split('\n'):
            if not line:
                continue
            
            parts = line.split('|')
            if len(parts) < 6:
                continue
            
            job = {
                'jobid': parts[0].strip(),
                'partition': parts[1].strip(),
                'name': parts[2].strip(),
                'user': parts[3].strip(),
                'reason': parts[4].strip(),
                'nodelist': parts[5].strip()
            }
            jobs.append(job)
        
        return jobs
    
    def get_node_resources(self, nodes: List[str]) -> Dict[str, Dict]:
        """Get current resource usage for nodes"""
        if not nodes:
            return {}
        
        node_list = ','.join(nodes)
        cmd = f"scontrol show node {node_list}"
        rc, stdout, stderr = self.run_command(cmd)
        
        if rc != 0:
            return {}
        
        resources = {}
        current_node = None
        
        for line in stdout.split('\n'):
            line = line.strip()
            if line.startswith('NodeName='):
                # Extract node name
                match = re.search(r'NodeName=(\S+)', line)
                if match:
                    current_node = match.group(1)
                    resources[current_node] = {
                        'state': 'unknown',
                        'cpus_total': 0,
                        'cpus_alloc': 0,
                        'gpus_total': 0,
                        'gpus_alloc': 0,
                        'mem_total': 0,
                        'mem_alloc': 0
                    }
                
                # Extract state
                match = re.search(r'State=(\S+)', line)
                if match and current_node:
                    resources[current_node]['state'] = match.group(1).lower()
            
            elif current_node and 'CPUAlloc=' in line:
                # Extract CPU info
                match = re.search(r'CPUAlloc=(\d+)', line)
                if match:
                    resources[current_node]['cpus_alloc'] = int(match.group(1))
                
                match = re.search(r'CPUTot=(\d+)', line)
                if match:
                    resources[current_node]['cpus_total'] = int(match.group(1))
            
            elif current_node and 'AllocMem=' in line:
                # Extract memory info
                match = re.search(r'AllocMem=(\d+)', line)
                if match:
                    resources[current_node]['mem_alloc'] = int(match.group(1))
                
                match = re.search(r'RealMemory=(\d+)', line)
                if match:
                    resources[current_node]['mem_total'] = int(match.group(1))
            
            elif current_node and 'Gres=' in line:
                # Extract GPU info if present
                match = re.search(r'gpu:(\d+)', line)
                if match:
                    resources[current_node]['gpus_total'] = int(match.group(1))
        
        return resources
    
    def analyze_job(self, job: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        Analyze a job to detect misleading status
        
        Returns dict with analysis or None if status is accurate
        """
        reason = job['reason']
        nodelist = job['nodelist']
        
        # Only analyze jobs with "nodes DOWN/DRAINED" message
        if 'DOWN' not in reason and 'DRAIN' not in reason:
            return None
        
        # Extract node names from nodelist (if present)
        nodes = self._extract_nodes(nodelist)
        if not nodes:
            return None
        
        # Check actual node resources
        resources = self.get_node_resources(nodes)
        if not resources:
            return None
        
        # Analyze what's really happening
        analysis = self._diagnose_resources(resources)
        
        if analysis['misleading']:
            return {
                'job': job,
                'nodes_checked': nodes,
                'real_reason': analysis['reason'],
                'details': analysis['details']
            }
        
        return None
    
    def _extract_nodes(self, nodelist: str) -> List[str]:
        """Extract individual node names from nodelist string"""
        # Handle formats like: node[01-03] or node01,node02
        nodes = []
        
        # Simple comma-separated list
        if ',' in nodelist and '[' not in nodelist:
            return [n.strip() for n in nodelist.split(',')]
        
        # Expanded range format: node[01-03]
        match = re.match(r'(\w+)\[([0-9,-]+)\]', nodelist)
        if match:
            prefix = match.group(1)
            ranges = match.group(2)
            
            for part in ranges.split(','):
                if '-' in part:
                    start, end = part.split('-')
                    # Preserve leading zeros
                    width = len(start)
                    for i in range(int(start), int(end) + 1):
                        nodes.append(f"{prefix}{i:0{width}d}")
                else:
                    nodes.append(f"{prefix}{part}")
        
        elif nodelist and not nodelist.startswith('('):
            # Single node or simple name
            nodes = [nodelist]
        
        return nodes
    
    def _diagnose_resources(self, resources: Dict[str, Dict]) -> Dict:
        """Diagnose actual resource constraints"""
        all_down = True
        all_cpus_full = True
        all_gpus_full = True
        all_mem_full = True
        
        cpu_details = []
        gpu_details = []
        mem_details = []
        
        for node, res in resources.items():
            state = res['state']
            
            # Check if node is actually down
            if state not in ['down', 'drained', 'draining', 'fail']:
                all_down = False
            
            # Check CPU availability
            if res['cpus_total'] > 0:
                cpu_avail = res['cpus_total'] - res['cpus_alloc']
                if cpu_avail > 0:
                    all_cpus_full = False
                cpu_details.append(f"{node}: {cpu_avail}/{res['cpus_total']} CPUs free")
            
            # Check GPU availability
            if res['gpus_total'] > 0:
                # For now, assume if GPUs exist, check if any job can get them
                # (more complex logic would check AllocTRES)
                gpu_details.append(f"{node}: {res['gpus_total']} GPUs")
            
            # Check memory availability
            if res['mem_total'] > 0:
                mem_avail = res['mem_total'] - res['mem_alloc']
                if mem_avail > 1000:  # >1GB available
                    all_mem_full = False
                mem_details.append(f"{node}: {mem_avail}MB/{res['mem_total']}MB free")
        
        # Determine if message is misleading
        misleading = not all_down
        
        if misleading:
            # Figure out real reason
            if all_cpus_full:
                return {
                    'misleading': True,
                    'reason': 'CPUs fully allocated',
                    'details': cpu_details
                }
            elif all_gpus_full and gpu_details:
                return {
                    'misleading': True,
                    'reason': 'GPUs fully allocated',
                    'details': gpu_details
                }
            elif all_mem_full:
                return {
                    'misleading': True,
                    'reason': 'Memory fully allocated',
                    'details': mem_details
                }
            else:
                return {
                    'misleading': True,
                    'reason': 'Resources busy (partition/priority)',
                    'details': ['Nodes available but allocated to higher priority jobs']
                }
        
        return {'misleading': False}
    
    def analyze_queue(self) -> List[Dict]:
        """Analyze entire queue for misleading statuses"""
        jobs = self.get_queue_jobs()
        misleading = []
        
        for job in jobs:
            analysis = self.analyze_job(job)
            if analysis:
                misleading.append(analysis)
        
        return misleading


def main():
    """Example usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze SLURM queue for misleading status messages')
    parser.add_argument('--cluster', required=True, help='Cluster name')
    parser.add_argument('--user', required=True, help='SSH user')
    parser.add_argument('--head-node', required=True, help='Head node hostname')
    
    args = parser.parse_args()
    
    analyzer = JobQueueAnalyzer(args.cluster, args.user, args.head_node)
    results = analyzer.analyze_queue()
    
    if not results:
        print("No misleading job statuses found")
        return
    
    print(f"\nFound {len(results)} jobs with misleading status messages:\n")
    
    for result in results:
        job = result['job']
        print(f"Job {job['jobid']} ({job['user']}): {job['name']}")
        print(f"  Status message: {job['reason']}")
        print(f"  Real reason: {result['real_reason']}")
        for detail in result['details']:
            print(f"    {detail}")
        print()


if __name__ == '__main__':
    sys.exit(main())
