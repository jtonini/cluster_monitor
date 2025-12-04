#!/usr/bin/env bash
# -*- coding: utf-8 -*-
# cluster_monitor_functions.sh
#
# Bash utility functions for cluster node monitoring
# Source this file to use the functions: source cluster_monitor_functions.sh

# ============================================================================
# Configuration
# ============================================================================
MONITOR_SCRIPT="${MONITOR_SCRIPT:-${HOME}/cluster_monitor/cluster_node_monitor.py}"
QUERY_SCRIPT="${QUERY_SCRIPT:-${HOME}/cluster_monitor/query_monitor_db.py}"
DB_PATH="${DB_PATH:-${HOME}/cluster_monitor.db}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# ============================================================================
# Cluster Connection Functions
# ============================================================================

# Check if we can connect to a cluster
# Usage: check_cluster_connection spydur
check_cluster_connection() {
    local cluster=$1
    
    if [[ "$cluster" == "spydur" ]]; then
        user="installer"
        head="spydur"
    elif [[ "$cluster" == "arachne" ]]; then
        user="zeus"
        head="arachne"
    else
        echo -e "${RED}Unknown cluster: $cluster${NC}"
        return 1
    fi
    
    if timeout 5 ssh -o ConnectTimeout=5 ${user}@${head} 'exit' 2>/dev/null; then
        echo -e "${GREEN}[OK] Can connect to ${cluster}${NC}"
        return 0
    else
        echo -e "${RED}[FAIL] Cannot connect to ${cluster}${NC}"
        return 1
    fi
}

# Get node status from SLURM
# Usage: get_node_status <cluster>
get_node_status() {
    local cluster=$1
    
    if [[ -z "$cluster" ]]; then
        echo "Usage: get_node_status <cluster>"
        return 1
    fi
    
    local user
    if [[ "$cluster" == "spydur" ]]; then
        user="installer"
    elif [[ "$cluster" == "arachne" ]]; then
        user="zeus"
    else
        echo "Unknown cluster: $cluster"
        return 1
    fi
    
    # Use sort -u to get unique node entries only
    ssh ${user}@${cluster} "sinfo -h -o '%N %T'" 2>/dev/null | sort -u
}

# Show detailed SLURM information for a node
# Usage: node_info <cluster> <node>
node_info() {
    local cluster=$1
    local node=$2
    
    if [[ -z "$cluster" || -z "$node" ]]; then
        echo "Usage: node_info <cluster> <node>"
        echo "Example: node_info spydur spdr01"
        return 1
    fi
    
    local user
    if [[ "$cluster" == "spydur" ]]; then
        user="installer"
    elif [[ "$cluster" == "arachne" ]]; then
        user="zeus"
    else
        echo "Unknown cluster: $cluster"
        return 1
    fi
    
    echo "============================================================"
    echo "LIVE NODE INFO: $cluster:$node"
    echo "============================================================"
    echo ""
    
    # Get detailed SLURM info
    ssh ${user}@${cluster} "scontrol show node $node"
    
    echo ""
    echo "------------------------------------------------------------"
    echo "JOBS ON THIS NODE:"
    echo "------------------------------------------------------------"
    
    # Show jobs running on this node
    ssh ${user}@${cluster} "squeue -w $node -o '%.18i %.9P %.20j %.8u %.2t %.10M %.6D %R' || echo 'No jobs running'"
}

# Check if a specific node is up
# Usage: is_node_up <cluster> <node>
is_node_up() {
    local cluster=$1
    local node=$2
    
    if [[ -z "$cluster" || -z "$node" ]]; then
        echo "Usage: is_node_up <cluster> <node>"
        return 1
    fi
    
    local user
    if [[ "$cluster" == "spydur" ]]; then
        user="installer"
    elif [[ "$cluster" == "arachne" ]]; then
        user="zeus"
    else
        echo "Unknown cluster: $cluster"
        return 1
    fi
    
    local state=$(ssh ${user}@${cluster} "sinfo -n $node -h -o '%T'" 2>/dev/null | head -1)
    
    if [[ -z "$state" ]]; then
        echo "Node not found: $node"
        return 1
    fi
    
    # Check for problem states
    # DOWN states: down, drain, drained, draining, fail, failing, maint, unknown
    # GOOD states: idle, mixed, allocated, completing
    if [[ "$state" =~ ^(down|drain|fail|maint|unk) ]]; then
        echo "[DOWN] $node is DOWN ($state)"
        return 1
    else
        echo "[OK] $node is UP ($state)"
        return 0
    fi
}

# ============================================================================
# Monitoring Functions
# ============================================================================

# Run a full monitoring check
# Usage: run_monitor [--no-recovery]
run_monitor() {
    echo -e "${BLUE}${BOLD}Running cluster monitor...${NC}"
    python3 "$MONITOR_SCRIPT" --monitor "$@"
}

# Check only (no recovery attempts)
# Usage: check_only
check_only() {
    echo -e "${BLUE}${BOLD}Checking cluster status (no recovery)...${NC}"
    python3 "$MONITOR_SCRIPT" --monitor --no-recovery
}

# Check specific cluster
# Usage: check_cluster spydur
check_cluster() {
    local cluster=$1
    echo -e "${BLUE}${BOLD}Checking ${cluster}...${NC}"
    python3 "$MONITOR_SCRIPT" --cluster "$cluster" --monitor
}

# ============================================================================
# Query Functions
# ============================================================================

# Show cluster health
# Usage: cluster_health
cluster_health() {
    python3 "$QUERY_SCRIPT" --health
}

# Show current status
# Usage: current_status [cluster]
current_status() {
    if [[ -n "$1" ]]; then
        python3 "$QUERY_SCRIPT" --current --cluster "$1"
    else
        python3 "$QUERY_SCRIPT" --current
    fi
}

# Show problem history
# Usage: problem_history [days] [cluster]
problem_history() {
    local days="${1:-7}"
    if [[ -n "$2" ]]; then
        python3 "$QUERY_SCRIPT" --problems --days "$days" --cluster "$2"
    else
        python3 "$QUERY_SCRIPT" --problems --days "$days"
    fi
}

# Show recovery stats
# Usage: recovery_stats [days] [cluster]
recovery_stats() {
    local days="${1:-7}"
    if [[ -n "$2" ]]; then
        python3 "$QUERY_SCRIPT" --recovery-stats --days "$days" --cluster "$2"
    else
        python3 "$QUERY_SCRIPT" --recovery-stats --days "$days"
    fi
}

# Show downtime report
# Usage: downtime_report [days] [cluster]
downtime_report() {
    local days="${1:-7}"
    if [[ -n "$2" ]]; then
        python3 "$QUERY_SCRIPT" --downtime --days "$days" --cluster "$2"
    else
        python3 "$QUERY_SCRIPT" --downtime --days "$days"
    fi
}

# Show node details
# Usage: node_details spydur spdr01 [days]
node_details() {
    local cluster=$1
    local node=$2
    local days="${3:-7}"
    python3 "$QUERY_SCRIPT" --node-detail "$cluster" "$node" --days "$days"
}

# ============================================================================
# Database Functions
# ============================================================================

# Show database statistics
# Usage: db_stats
db_stats() {
    if [[ ! -f "$DB_PATH" ]]; then
        echo -e "${RED}Database not found: $DB_PATH${NC}"
        return 1
    fi
    
    echo -e "${BLUE}${BOLD}Database Statistics${NC}"
    echo "File: $DB_PATH"
    echo "Size: $(du -h "$DB_PATH" | cut -f1)"
    echo ""
    
    sqlite3 "$DB_PATH" <<EOF
SELECT 'Node Status Records: ' || COUNT(*) FROM node_status;
SELECT 'Node Events: ' || COUNT(*) FROM node_events;
SELECT 'Recovery Attempts: ' || COUNT(*) FROM recovery_attempts;
SELECT 'Oldest Record: ' || MIN(timestamp) FROM node_status;
SELECT 'Newest Record: ' || MAX(timestamp) FROM node_status;
EOF
}

# Cleanup old database records
# Usage: db_cleanup [days]
db_cleanup() {
    local days="${1:-90}"
    
    if [[ ! -f "$DB_PATH" ]]; then
        echo -e "${RED}Database not found: $DB_PATH${NC}"
        return 1
    fi
    
    echo -e "${GREEN}Cleaning records older than $days days...${NC}"
    
    sqlite3 "$DB_PATH" <<EOF
DELETE FROM node_status WHERE timestamp < datetime('now', '-$days days');
DELETE FROM node_events WHERE timestamp < datetime('now', '-$days days');
DELETE FROM recovery_attempts WHERE timestamp < datetime('now', '-$days days');
VACUUM;
EOF
    
    echo -e "${GREEN}[OK] Cleanup complete${NC}"
    db_stats
}

# Backup database
# Usage: db_backup [backup_path]
db_backup() {
    local backup_path="${1:-${DB_PATH}.backup.$(date +%Y%m%d_%H%M%S)}"
    
    if [[ ! -f "$DB_PATH" ]]; then
        echo -e "${RED}Database not found: $DB_PATH${NC}"
        return 1
    fi
    
    echo -e "${BLUE}Backing up database...${NC}"
    sqlite3 "$DB_PATH" ".backup '$backup_path'"
    
    if [[ -f "$backup_path" ]]; then
        echo -e "${GREEN}[OK] Backup created: $backup_path${NC}"
        echo "Size: $(du -h "$backup_path" | cut -f1)"
    else
        echo -e "${RED}[FAIL] Backup failed${NC}"
        return 1
    fi
}

# Query database directly
# Usage: db_query "SELECT * FROM node_status LIMIT 10"
db_query() {
    local query="$1"
    
    if [[ ! -f "$DB_PATH" ]]; then
        echo -e "${RED}Database not found: $DB_PATH${NC}"
        return 1
    fi
    
    sqlite3 -header -column "$DB_PATH" "$query"
}

# ============================================================================
# Reporting Functions
# ============================================================================

# Generate report
# Usage: generate_report [days]
generate_report() {
    local days="${1:-7}"
    python3 "$MONITOR_SCRIPT" --report --days "$days"
}

# Email report
# Usage: email_report email@domain.com [days]
email_report() {
    local email="$1"
    local days="${2:-7}"
    
    if [[ -z "$email" ]]; then
        echo -e "${RED}Usage: email_report email@domain.com [days]${NC}"
        return 1
    fi
    
    python3 "$MONITOR_SCRIPT" --report --days "$days" | \
        mail -s "Cluster Monitor Report (Last $days days)" "$email"
    
    echo -e "${GREEN}[OK] Report sent to $email${NC}"
}

# ============================================================================
# Utility Functions
# ============================================================================

# Watch cluster status (refresh every N seconds)
# Usage: watch_clusters [interval]
watch_clusters() {
    local interval="${1:-60}"
    
    while true; do
        clear
        echo -e "${BOLD}Cluster Status - $(date)${NC}"
        echo ""
        cluster_health
        echo ""
        echo -e "${BLUE}Refreshing in ${interval}s... (Ctrl+C to stop)${NC}"
        sleep "$interval"
    done
}

# Get problem node count
# Usage: problem_count [cluster]
problem_count() {
    if [[ ! -f "$DB_PATH" ]]; then
        echo "0"
        return
    fi
    
    if [[ -n "$1" ]]; then
        sqlite3 "$DB_PATH" "
            SELECT COUNT(*) FROM latest_node_status 
            WHERE is_available = 0 AND cluster = '$1'
        "
    else
        sqlite3 "$DB_PATH" "
            SELECT COUNT(*) FROM latest_node_status 
            WHERE is_available = 0
        "
    fi
}

# Alert if problems detected
# Usage: alert_if_problems
alert_if_problems() {
    local count=$(problem_count)
    
    if [[ "$count" -gt 0 ]]; then
        echo -e "${RED}[WARNING] $count node(s) with problems!${NC}"
        problem_history 1
        return 1
    else
        echo -e "${GREEN}[OK] All nodes healthy${NC}"
        return 0
    fi
}

# Quick status check (returns 0 if all healthy)
# Usage: quick_check
quick_check() {
    local count=$(problem_count)
    return "$count"
}

# ============================================================================
# SSH Recovery Functions
# ============================================================================

# Manually resume a node
# Usage: resume_node spydur spdr01
resume_node() {
    local cluster=$1
    local node=$2
    
    if [[ "$cluster" == "spydur" ]]; then
        user="installer"
        head="spydur"
        # spydur: no sudo, must impersonate slurm user
        resume_cmd="sudo -u slurm scontrol update nodename=${node} state=resume"
    elif [[ "$cluster" == "arachne" ]]; then
        user="zeus"
        head="arachne"
        # arachne: zeus is in wheel group, has sudo access
        resume_cmd="sudo scontrol update nodename=${node} state=resume"
    else
        echo -e "${RED}Unknown cluster: $cluster${NC}"
        return 1
    fi
    
    echo -e "${BLUE}Resuming node ${cluster}:${node}...${NC}"
    ssh ${user}@${head} "$resume_cmd"
    
    sleep 5
    is_node_up "$cluster" "$node"
}

# Manually restart slurmd on a node
# Usage: restart_slurmd spydur spdr01
restart_slurmd() {
    local cluster=$1
    local node=$2
    
    if [[ "$cluster" == "spydur" ]]; then
        user="installer"
        head="spydur"
        # installer has NOPASSWD access to systemctl for slurmd
        restart_cmd="ssh ${node} 'sudo systemctl restart slurmd'"
    elif [[ "$cluster" == "arachne" ]]; then
        user="zeus"
        head="arachne"
        # zeus logs in as root on nodes, no sudo needed
        restart_cmd="ssh ${node} 'systemctl restart slurmd'"
    else
        echo -e "${RED}Unknown cluster: $cluster${NC}"
        return 1
    fi
    
    echo -e "${BLUE}Restarting slurmd on ${cluster}:${node}...${NC}"
    ssh ${user}@${head} "$restart_cmd"
    
    sleep 5
    is_node_up "$cluster" "$node"
}

# ============================================================================
# Help Function
# ============================================================================

# Show available functions
# Usage: monitor_help
monitor_help() {
    cat <<EOF

Cluster Monitor Bash Functions

Connection Functions:
  check_cluster_connection <cluster>    - Test SSH connection
  get_node_status <cluster>             - Get node status from SLURM
  is_node_up <cluster> <node>           - Check if specific node is up

Monitoring Functions:
  run_monitor [--no-recovery]           - Run full monitoring check
  check_only                            - Check status without recovery
  check_cluster <cluster>               - Check specific cluster

Query Functions:
  cluster_health                        - Show cluster health summary
  current_status [cluster]              - Show current node status
  problem_history [days] [cluster]      - Show problem history
  recovery_stats [days] [cluster]       - Show recovery statistics
  downtime_report [days] [cluster]      - Show downtime report
  node_details <cluster> <node> [days]  - Show specific node details
  node_info <cluster> <node>            - Show live SLURM node info

Database Functions:
  db_stats                              - Show database statistics
  db_cleanup [days]                     - Cleanup old records
  db_backup [path]                      - Backup database
  db_query "SQL"                        - Execute SQL query

Reporting Functions:
  generate_report [days]                - Generate text report
  email_report <email> [days]           - Email report

Utility Functions:
  watch_clusters [interval]             - Watch status (auto-refresh)
  problem_count [cluster]               - Get count of problem nodes
  alert_if_problems                     - Alert if problems exist
  quick_check                           - Quick health check (exit code)

Recovery Functions:
  resume_node <cluster> <node>          - Manually resume a node
  restart_slurmd <cluster> <node>       - Restart slurmd service

Examples:
  cluster_health
  problem_history 7 spydur
  node_details spydur spdr05
  node_info spydur spdr01
  resume_node spydur spdr01
  watch_clusters 30

EOF
}

# Show help on load if requested
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    monitor_help
fi
