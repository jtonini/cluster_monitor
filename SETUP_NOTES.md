# Post-Installation Setup Notes

## Email Configuration (CRITICAL)

If your control host cannot send external emails directly, use local aliases to forward through your institution's mail system.

### Setup Email Aliases
```bash
# Edit aliases file (requires sudo)
sudo vim /etc/aliases

# Add aliases for your monitoring accounts:
monitoring: your-email@institution.edu
admin: your-email@institution.edu

# Rebuild aliases database
sudo newaliases
```

### Update Monitoring Config

Edit `~/.config/cluster_monitor/config.toml`:
```toml
[email]
enabled = true
from = "monitoring@your-control-host"
to = ["monitoring"]      # Use local alias, not direct email
cc = ["admin"]           # Use local alias, not direct email
smtp_server = "localhost"
smtp_port = 25
```

**Note:** Use local usernames (aliases) instead of full email addresses. The aliases will forward to your actual email.

### Enable and Start Postfix
```bash
# Start postfix service
sudo systemctl start postfix

# Enable postfix to start on boot
sudo systemctl enable postfix

# Verify it's running
systemctl status postfix
```

### Clean Mail Queue (If Needed)

If you have stuck emails from testing:
```bash
# Check mail queue status
mailq

# Clear all stuck messages
sudo postsuper -d ALL
```

### Test Email Delivery
```bash
# Send test email to your local alias
echo "Test email from cluster monitor" | mail -s "Test" monitoring

# Should arrive at your actual email address
```

## Cron Setup

After running `./setup_cron.sh`, verify the paths are correct for your installation:
```bash
# Check cron jobs
crontab -l | grep cluster_monitor

# Verify paths match your actual installation directory
# Example: /home/your-user/cluster_monitor/cluster_node_monitor.py
```

If paths are incorrect, re-run setup from the correct directory:
```bash
cd ~/cluster_monitor  # or your actual installation directory
./setup_cron.sh
```

The setup script will detect your current directory and use the correct paths.

## New Functions Added

### node_info - Live SLURM Node Details

View detailed live information about a specific node:
```bash
# Load functions
source cluster_monitor_functions.sh

# View node details
node_info <cluster> <node>

# Examples:
node_info spydur spdr01
node_info arachne node52
```

**Output includes:**
- CPU allocation (total, allocated, idle)
- Memory usage (total, free)
- GPU information (if available)
- Jobs currently running on the node
- SLURM state and configuration

## Troubleshooting

### Emails Not Arriving

**Symptoms:** No notification emails received

**Check:**
1. Postfix running: `systemctl status postfix`
2. Aliases configured: `cat /etc/aliases | grep your-alias`
3. Queue not stuck: `mailq` (should be empty or minimal)
4. Local delivery works: `echo "test" | mail -s "test" your-local-alias`

**Common causes:**
- Postfix not started or enabled
- Aliases not rebuilt after editing
- Mail queue full of bounced messages
- Trying to send to external addresses directly

### Cron Jobs Not Running

**Symptoms:** No automatic monitoring, empty cron logs

**Check:**
1. Cron paths correct: `crontab -l`
2. Script executable: `ls -l ~/cluster_monitor/*.py`
3. Check cron log: `tail ~/cluster_monitor_cron.log`
4. Look for errors like "No such file or directory"

**Fix:**
- Run `./setup_cron.sh` from your installation directory
- Ensure scripts have execute permission: `chmod +x *.py *.sh`

### Query Shows Only One Cluster

**Symptoms:** `./query_monitor_db.py --current` only shows one cluster

**Cause:** Original code had SQL bug (max timestamp across all clusters)

**Fix:** This installation includes the corrected version using per-cluster max timestamp.

**Verify fix:**
```bash
# Should show both clusters
./query_monitor_db.py --current
```

### Duplicate Nodes in Output

**Symptoms:** Nodes appear multiple times in `get_node_status`

**Cause:** Nodes belong to multiple SLURM partitions

**Fix:** Use `sort -u` to show unique nodes (already applied in bash functions)

**Verify fix:**
```bash
source cluster_monitor_functions.sh
get_node_status spydur   # Each node should appear once
```

### "No such column: recovery_action" Error

**Symptoms:** `node_details` command fails with SQL error

**Cause:** Query used wrong column names for database schema

**Fix:** This installation includes corrected column names (command, output vs recovery_action, error_message)

## Configuration Tips

### Email Recipients

Use multiple aliases for different notification levels:
```toml
[email]
to = ["hpc-admins"]           # Primary admin list
cc = ["hpc-backup"]           # Backup/secondary admins
```

Define in `/etc/aliases`:
```
hpc-admins: admin1@inst.edu, admin2@inst.edu
hpc-backup: backup@inst.edu
```

### Monitoring Frequency

Default is every 5 minutes. Adjust in crontab:
```bash
# Every 5 minutes (default)
*/5 * * * * /path/to/cluster_node_monitor.py --monitor

# Every 10 minutes
*/10 * * * * /path/to/cluster_node_monitor.py --monitor

# Every hour
0 * * * * /path/to/cluster_node_monitor.py --monitor
```

### Report Schedule

Customize daily/weekly reports in crontab:
```bash
# Daily report at 8 AM
0 8 * * * /path/to/cluster_node_monitor.py --report --days 1 | mail -s "Daily Report" monitoring

# Weekly report Monday 9 AM
0 9 * * 1 /path/to/cluster_node_monitor.py --report --days 7 | mail -s "Weekly Report" monitoring
```

## File Locations

After installation, key files are located at:
```
~/cluster_monitor/                      # Installation directory
~/.config/cluster_monitor/config.toml  # Configuration file
~/cluster_monitor.db                   # SQLite database
~/cluster_monitor.log                  # Main log file
~/cluster_monitor_cron.log             # Cron execution log
```

## Getting Help

### View Available Functions
```bash
source cluster_monitor_functions.sh
monitor_help
```

### Check System Status
```bash
# Overall health
cluster_health

# Current status
current_status

# Recent problems
problem_history 7

# Database stats
db_stats
```

### Manual Monitoring Run
```bash
# Full monitoring with recovery
./cluster_node_monitor.py --monitor

# Check only (no recovery)
./cluster_node_monitor.py --monitor --no-recovery

# Generate report
./cluster_node_monitor.py --report --days 7
```
