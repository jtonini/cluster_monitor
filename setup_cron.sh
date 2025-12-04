#!/usr/bin/env bash
# -*- coding: utf-8 -*-
# setup_cron.sh
#
# Setup cron jobs for cluster node monitoring
# Run this script on badenpowell as user cazuza

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONITOR_SCRIPT="${SCRIPT_DIR}/cluster_node_monitor.py"
CRON_USER="${USER}"

echo "Cluster Node Monitor - Cron Setup"
echo "=================================="
echo ""
echo "This will setup cron jobs to monitor your clusters automatically"
echo "Script location: ${MONITOR_SCRIPT}"
echo "User: ${CRON_USER}"
echo ""

# Check if monitor script exists
if [[ ! -f "${MONITOR_SCRIPT}" ]]; then
    echo "ERROR: Monitor script not found at ${MONITOR_SCRIPT}"
    exit 1
fi

# Make script executable
chmod +x "${MONITOR_SCRIPT}"

# Backup existing crontab
if crontab -l >/dev/null 2>&1; then
    echo "Backing up existing crontab..."
    crontab -l > "${HOME}/crontab_backup_$(date +%Y%m%d_%H%M%S).txt"
fi

# Create temporary cron file
TEMP_CRON=$(mktemp)

# Get existing crontab (if any) and remove old cluster monitor entries
if crontab -l >/dev/null 2>&1; then
    crontab -l | grep -v "cluster_node_monitor" > "${TEMP_CRON}" || true
fi

# Add new cron jobs
cat >> "${TEMP_CRON}" << EOF

# Cluster Node Monitor - Added by setup_cron.sh
# Check clusters every 5 minutes and attempt recovery
*/5 * * * * ${MONITOR_SCRIPT} --monitor >> ${HOME}/cluster_monitor_cron.log 2>&1

# Generate daily report at 8 AM
0 8 * * * ${MONITOR_SCRIPT} --report --days 1 | mail -s "Daily Cluster Status Report" ${CRON_USER}@badenpowell

# Generate weekly report every Monday at 8 AM
0 8 * * 1 ${MONITOR_SCRIPT} --report --days 7 | mail -s "Weekly Cluster Status Report" ${CRON_USER}@badenpowell

EOF

# Install new crontab
crontab "${TEMP_CRON}"
rm "${TEMP_CRON}"

echo ""
echo "OK Cron jobs installed successfully!"
echo ""
echo "Scheduled jobs:"
echo "  - Monitor clusters every 5 minutes with auto-recovery"
echo "  - Daily report at 8:00 AM"
echo "  - Weekly report every Monday at 8:00 AM"
echo ""
echo "To view your crontab: crontab -l"
echo "To edit your crontab: crontab -e"
echo "To remove cluster monitor cron jobs: crontab -e (then delete the lines)"
echo ""
echo "Logs will be written to:"
echo "  - ${HOME}/cluster_monitor.log (main log)"
echo "  - ${HOME}/cluster_monitor_cron.log (cron execution log)"
echo ""
echo "Database location: ${HOME}/cluster_monitor.db"
echo ""
