#!/usr/bin/env bash
# -*- coding: utf-8 -*-
# dashboard.sh
#
# Quick dashboard for cluster status
# Shows real-time status and recent issues

set -euo pipefail

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
BOLD='\033[1m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONITOR="${SCRIPT_DIR}/cluster_node_monitor.py"
QUERY="${SCRIPT_DIR}/query_monitor_db.py"

clear

echo -e "${BOLD}============================================================${NC}"
echo -e "${BOLD}          CLUSTER NODE MONITOR - DASHBOARD                 ${NC}"
echo -e "${BOLD}============================================================${NC}"
echo ""
echo -e "Generated: $(date '+%Y-%m-%d %H:%M:%S')"
echo -e "Host: $(hostname)"
echo ""

# Function to check if database exists
check_db() {
    if [[ ! -f "${HOME}/cluster_monitor.db" ]]; then
        echo -e "${RED}X Database not found!${NC}"
        echo "Run the monitor first: ${MONITOR} --monitor"
        exit 1
    fi
}

# Function to display cluster status with colors
show_cluster_status() {
    local cluster=$1
    
    echo -e "\n${BLUE}${BOLD}--- $cluster --------------------------------------------${NC}"
    
    # Get real-time status via SSH
    if [[ "$cluster" == "spydur" ]]; then
        user="installer"
        head="spydur"
    else
        user="zeus"
        head="arachne"
    fi
    
    # Check if we can reach the cluster
    if timeout 5 ssh -o ConnectTimeout=5 ${user}@${head} 'exit' 2>/dev/null; then
        echo -e "${GREEN}[OK] Cluster reachable${NC}"
        
        # Get node status
        node_status=$(ssh ${user}@${head} 'sinfo -h -N -o "%N %T"' 2>/dev/null || echo "")
        
        if [[ -n "$node_status" ]]; then
            # Count states
            total=$(echo "$node_status" | wc -l)
            idle=$(echo "$node_status" | grep -i "idle" | wc -l)
            alloc=$(echo "$node_status" | grep -i "alloc" | wc -l)
            mix=$(echo "$node_status" | grep -i "mix" | wc -l)
            down=$(echo "$node_status" | grep -iE "down|drain|fail" | wc -l)
            
            healthy=$((idle + alloc + mix))
            
            echo ""
            echo -e "  Total nodes:  ${BOLD}$total${NC}"
            echo -e "  ${GREEN}Healthy:      $healthy${NC} (idle: $idle, allocated: $alloc, mixed: $mix)"
            
            if [[ $down -gt 0 ]]; then
                echo -e "  ${RED}Problem:      $down${NC}"
                echo ""
                echo -e "  ${RED}Problem nodes:${NC}"
                echo "$node_status" | grep -iE "down|drain|fail" | while read node state; do
                    echo -e "    ${RED}[X]${NC} $node - $state"
                done
            else
                echo -e "  ${GREEN}Problem:      0${NC}"
            fi
        else
            echo -e "${YELLOW}[!] Could not get node status${NC}"
        fi
    else
        echo -e "${RED}[X] Cluster unreachable (SSH timeout)${NC}"
    fi
}

# Function to show recent issues
show_recent_issues() {
    echo -e "\n${BLUE}${BOLD}--- RECENT ISSUES (Last 24 hours) ----------------------${NC}\n"
    
    if [[ -f "${HOME}/cluster_monitor.db" ]]; then
        # Query database for recent problems
        recent=$(sqlite3 "${HOME}/cluster_monitor.db" "
            SELECT cluster, node_name, COUNT(*) as count
            FROM node_events
            WHERE timestamp > datetime('now', '-1 day')
            AND severity IN ('warning', 'error', 'critical')
            AND event_type = 'node_down'
            GROUP BY cluster, node_name
            ORDER BY count DESC
            LIMIT 10
        " 2>/dev/null || echo "")
        
        if [[ -n "$recent" ]]; then
            echo -e "  ${BOLD}Cluster    Node            Count${NC}"
            echo "  -------------------------------------"
            echo "$recent" | while IFS='|' read cluster node count; do
                if [[ $count -gt 5 ]]; then
                    echo -e "  ${RED}$cluster      $node            $count${NC}"
                elif [[ $count -gt 2 ]]; then
                    echo -e "  ${YELLOW}$cluster      $node            $count${NC}"
                else
                    echo -e "  $cluster      $node            $count"
                fi
            done
        else
            echo -e "  ${GREEN}[OK] No issues in the last 24 hours${NC}"
        fi
    else
        echo -e "  ${YELLOW}[!] Database not available${NC}"
    fi
}

# Function to show recovery stats
show_recovery_stats() {
    echo -e "\n${BLUE}${BOLD}--- RECOVERY STATISTICS (Last 7 days) ------------------${NC}\n"
    
    if [[ -f "${HOME}/cluster_monitor.db" ]]; then
        stats=$(sqlite3 "${HOME}/cluster_monitor.db" "
            SELECT cluster,
                   SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                   SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed
            FROM recovery_attempts
            WHERE timestamp > datetime('now', '-7 days')
            GROUP BY cluster
        " 2>/dev/null || echo "")
        
        if [[ -n "$stats" ]]; then
            echo -e "  ${BOLD}Cluster    Success  Failed   Rate${NC}"
            echo "  ------------------------------------"
            echo "$stats" | while IFS='|' read cluster success failed; do
                total=$((success + failed))
                if [[ $total -gt 0 ]]; then
                    rate=$(awk "BEGIN {printf \"%.1f\", ($success/$total)*100}")
                    if (( $(echo "$rate > 80" | bc -l) )); then
                        color=$GREEN
                    elif (( $(echo "$rate > 50" | bc -l) )); then
                        color=$YELLOW
                    else
                        color=$RED
                    fi
                    echo -e "  $cluster      ${color}$success        $failed       ${rate}%${NC}"
                fi
            done
        else
            echo -e "  ${GREEN}[OK] No recovery attempts in the last 7 days${NC}"
        fi
    fi
}

# Function to show system info
show_system_info() {
    echo -e "\n${BLUE}${BOLD}--- MONITORING SYSTEM STATUS ---------------------------${NC}\n"
    
    # Check if monitor is in cron
    if crontab -l 2>/dev/null | grep -q "cluster_node_monitor"; then
        echo -e "  ${GREEN}[OK] Cron jobs installed${NC}"
        cron_line=$(crontab -l | grep "cluster_node_monitor" | grep "monitor" | head -1)
        if [[ -n "$cron_line" ]]; then
            echo -e "    Schedule: Every 5 minutes"
        fi
    else
        echo -e "  ${YELLOW}[!] No cron jobs found${NC}"
        echo -e "    Run: ${BOLD}./setup_cron.sh${NC}"
    fi
    
    # Check database size
    if [[ -f "${HOME}/cluster_monitor.db" ]]; then
        db_size=$(du -h "${HOME}/cluster_monitor.db" | cut -f1)
        echo -e "  Database: ${db_size}"
        
        # Count records
        record_count=$(sqlite3 "${HOME}/cluster_monitor.db" "SELECT COUNT(*) FROM node_status" 2>/dev/null || echo "0")
        echo -e "  Records:  $record_count status checks"
    fi
    
    # Check log size
    if [[ -f "${HOME}/cluster_monitor.log" ]]; then
        log_size=$(du -h "${HOME}/cluster_monitor.log" | cut -f1)
        echo -e "  Log file: ${log_size}"
    fi
    
    # Last check time
    if [[ -f "${HOME}/cluster_monitor.db" ]]; then
        last_check=$(sqlite3 "${HOME}/cluster_monitor.db" "SELECT MAX(timestamp) FROM node_status" 2>/dev/null || echo "Never")
        echo -e "  Last check: $last_check"
    fi
}

# Main execution
check_db

# Show status for each cluster
show_cluster_status "spydur"
show_cluster_status "arachne"

# Show recent issues
show_recent_issues

# Show recovery statistics
show_recovery_stats

# Show system info
show_system_info

echo ""
echo -e "${BOLD}------------------------------------------------------------${NC}"
echo ""
echo "Commands:"
echo "  Full health report:     ./query_monitor_db.py --health"
echo "  Current status:         ./query_monitor_db.py --current"
echo "  Problem history:        ./query_monitor_db.py --problems"
echo "  Node details:           ./query_monitor_db.py --node-detail <cluster> <node>"
echo "  Manual check:           ./cluster_node_monitor.py --monitor"
echo ""
echo "Press Ctrl+C to exit, or wait for auto-refresh..."

# Optional: Auto-refresh every 60 seconds
# Uncomment the following lines to enable
# sleep 60
# exec "$0"
