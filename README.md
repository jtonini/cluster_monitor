# Cluster Node Monitor

Automated monitoring and recovery system for SLURM clusters **spydur** and **arachne**.

## Overview

This monitoring system:
- Detects node failures using SLURM's sinfo command
- Attempts automatic recovery of down nodes
- Logs all events to SQLite database
- Sends email notifications for critical issues
- Generates reports on cluster health and downtime

## Repository Structure

```
cluster_monitor/
+-- cluster_node_monitor.py           # Main monitoring script
+-- cluster_monitor_dbclass.py        # Database operations class
+-- cluster_monitor_schema.sql        # SQL database schema
+-- cluster_monitor.toml              # Configuration file (template)
+-- query_monitor_db.py               # Database query tool
+-- cluster_monitor_functions.sh      # Bash utility functions
+-- dashboard.sh                      # Quick status dashboard
+-- setup_cron.sh                     # Cron job installer
+-- README.md                         # This file
+-- INSTALL.md                        # Quick start guide
+-- HPCLIB_DEPENDENCIES.md           # hpclib requirements
\-- LICENSE                           # MIT License
```

## Architecture

```
badenpowell (cazuza)
    |
    +- SSH --> spydur (installer)
    |           \- Monitors: spdr01-18, spdr50-61 (30 nodes)
    |
    \- SSH --> arachne (zeus)
                \- Monitors: node01-03, node51-53 (6 nodes)
```

### Key Components

1. **cluster_node_monitor.py** - Main monitoring script
2. **query_monitor_db.py** - Database query and reporting tool
3. **setup_cron.sh** - Automated cron job installation
4. **cluster_monitor.db** - SQLite database (auto-created)
5. **config.toml** - Configuration file

## Prerequisites

- Python 3.8 or higher
- SSH key authentication configured:
  - cazuza@badenpowell -> installer@spydur
  - cazuza@badenpowell -> zeus@arachne
- SLURM cluster management system

**Note:** All required hpclib files (urdb.py, dorunrun.py, fname.py) are included in this repository.

## Installation

### Option 1: Install from Git (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/jtonini/cluster_monitor.git
cd cluster_monitor

# 2. Make scripts executable
chmod +x *.py *.sh

# 3. Run initial setup
./cluster_node_monitor.py --monitor --no-recovery

# 4. Configure
vim ~/.config/cluster_monitor/config.toml
# (update email and cluster settings)

# 5. Install cron
./setup_cron.sh

# Done! System is now monitoring automatically
```

### Option 2: Manual Installation


### 1. Clone or Copy Files

On **badenpowell** as user **cazuza**:

```bash
# Create directory for the monitor
mkdir -p ~/cluster_monitor
cd ~/cluster_monitor

# Copy the scripts
# (Assuming you have them in your current directory)
cp cluster_node_monitor.py ~/cluster_monitor/
cp query_monitor_db.py ~/cluster_monitor/
cp setup_cron.sh ~/cluster_monitor/

# Make scripts executable
chmod +x cluster_node_monitor.py
chmod +x query_monitor_db.py
chmod +x setup_cron.sh
```

### 2. Verify hpclib Installation

```bash
# Check if hpclib is available
ls ~/hpclib/

# Should see files like: urdb.py, dorunrun.py, fname.py, etc.
```

### 3. Install Python Dependencies

```bash
# If using Python < 3.11, install tomli
pip install tomli --break-system-packages
```

### 4. Test SSH Connectivity

```bash
# Test spydur connection
ssh installer@spydur 'sinfo -h -N -o "%N %T"'

# Test arachne connection
ssh zeus@arachne 'sinfo -h -N -o "%N %T"'
```

Both commands should return node status information.

### 5. Configure Email Settings

```bash
# Run the monitor once to create default config
./cluster_node_monitor.py --monitor

# Edit the configuration
vim ~/.config/cluster_monitor/config.toml
```

Update the email settings:

```toml
[email]
enabled = true
from = "cazuza@badenpowell"
to = ["your-email@domain.com"]  # Update this!
smtp_server = "localhost"
smtp_port = 25
```

### 6. Setup Cron Jobs

```bash
# Install automated monitoring
./setup_cron.sh
```

This will setup:
- Monitoring every 5 minutes with auto-recovery
- Daily status report at 8 AM
- Weekly status report every Monday at 8 AM

## Usage

### Using Bash Functions (Recommended)

Source the bash functions for convenient access:

```bash
# Source the functions
source ~/cluster_monitor/cluster_monitor_functions.sh

# Show available functions
monitor_help

# Quick examples
cluster_health                    # Show cluster health
problem_history 7 spydur         # Show 7-day problem history for spydur
node_details spydur spdr05       # Details for specific node
watch_clusters 30                 # Auto-refreshing dashboard (30s interval)
resume_node spydur spdr01        # Manually resume a node
```

### Manual Monitoring

```bash
# Monitor all clusters with automatic recovery
./cluster_node_monitor.py --monitor

# Monitor without attempting recovery (check only)
./cluster_node_monitor.py --monitor --no-recovery

# Monitor specific cluster only
./cluster_node_monitor.py --cluster spydur --monitor
```

### Generate Reports

```bash
# Generate 7-day status report
./cluster_node_monitor.py --report

# Generate 30-day report
./cluster_node_monitor.py --report --days 30
```

### Query Database

```bash
# Show overall cluster health
./query_monitor_db.py --health

# Show current status of all nodes
./query_monitor_db.py --current

# Show current status for specific cluster
./query_monitor_db.py --current --cluster spydur

# Show problem history (last 7 days)
./query_monitor_db.py --problems

# Show problem history (last 30 days)
./query_monitor_db.py --problems --days 30

# Show recovery statistics
./query_monitor_db.py --recovery-stats

# Show downtime report
./query_monitor_db.py --downtime

# Show detailed info for specific node
./query_monitor_db.py --node-detail spydur spdr01

# List all nodes by cluster
./query_monitor_db.py --list-nodes
```

## Configuration

### Main Configuration File

Location: `~/.config/cluster_monitor/config.toml`

```toml
[email]
enabled = true
from = "cazuza@badenpowell"
to = ["your-email@domain.com"]
smtp_server = "localhost"
smtp_port = 25

[spydur]
user = "installer"
head_node = "spydur"
# Nodes are auto-populated, but can be overridden:
# nodes = ["spdr01", "spdr02", ...]

[arachne]
user = "zeus"
head_node = "arachne"
# Nodes are auto-populated, but can be overridden:
# nodes = ["node01", "node02", ...]

[monitoring]
check_interval = 300  # 5 minutes (set via cron)
max_recovery_attempts = 3
recovery_wait_time = 60  # seconds
```

### Recovery Commands

By default, the monitor attempts these recovery commands:

**Spydur:**
1. `sudo -u slurm scontrol update nodename=<node> state=resume` - Resume node (impersonate slurm user)
2. `ssh <node> "sudo systemctl restart slurmd"` - Restart slurmd service (installer has NOPASSWD)

**Arachne:**
1. `sudo scontrol update nodename=<node> state=resume` - Resume node (zeus has sudo on head node)
2. `ssh <node> "systemctl restart slurmd"` - Restart slurmd service (zeus logs in as root on nodes)

You can customize these in the script's `CLUSTERS` configuration or in `config.toml`.

## Database Schema

### Tables

**node_status** - Records every status check
- timestamp, cluster, node_name, status, slurm_state, is_available, checked_from

**node_events** - Records significant events
- timestamp, cluster, node_name, event_type, details, severity

**recovery_attempts** - Records recovery attempts
- timestamp, cluster, node_name, command, exit_code, output, success

### File Locations

- Database: `~/cluster_monitor.db`
- Main log: `~/cluster_monitor.log`
- Cron log: `~/cluster_monitor_cron.log`
- Config: `~/.config/cluster_monitor/config.toml`

## Monitoring Logic

### Node State Detection

The monitor checks SLURM node states and considers these as problematic:
- `down` - Node is down
- `drain` / `drng` - Node is draining or drained
- `fail` / `failing` - Node has failed
- `maint` - Node in maintenance
- `unk` / `unknown` - Unknown state

Normal states (no action taken):
- `idle` - Available for jobs
- `alloc` - Running jobs
- `mix` - Partially allocated

### Recovery Process

1. **Detect** problem node via `sinfo`
2. **Log** event to database
3. **Attempt** recovery commands in sequence:
   - Resume in SLURM
   - Restart slurmd service
4. **Wait** 10 seconds
5. **Verify** node is back online
6. **Log** recovery result
7. **Notify** via email if configured

### Email Notifications

Notifications are sent for:
- Warning: **Warning**: 1-3 nodes down
- Critical: **Critical**: 4+ nodes down
- Failed: **Error**: Recovery failures

## Troubleshooting

### Monitor Not Running

```bash
# Check if database exists
ls -lh ~/cluster_monitor.db

# Check log files
tail -f ~/cluster_monitor.log
tail -f ~/cluster_monitor_cron.log

# Verify cron jobs
crontab -l | grep cluster_monitor
```

### SSH Connection Issues

```bash
# Test SSH connectivity
ssh installer@spydur hostname
ssh zeus@arachne hostname

# Check SSH keys
ls -la ~/.ssh/

# Test with verbose output
ssh -v installer@spydur 'sinfo'
```

### Database Locked

```bash
# Check if another process is running
ps aux | grep cluster_node_monitor

# If stuck, kill process
pkill -f cluster_node_monitor
```

### Recovery Not Working

```bash
# Check if you have sudo access on nodes
ssh installer@spydur 'ssh spdr01 "sudo systemctl status slurmd"'

# Manually test recovery command
ssh installer@spydur 'scontrol update nodename=spdr01 state=resume'
```

### Email Not Sending

```bash
# Test mail system
echo "Test" | mail -s "Test Subject" cazuza@badenpowell

# Check SMTP configuration in config.toml
cat ~/.config/cluster_monitor/config.toml
```

## Maintenance

### Backup Database

```bash
# Create backup
cp ~/cluster_monitor.db ~/cluster_monitor_backup_$(date +%Y%m%d).db

# Or use SQLite's backup command
sqlite3 ~/cluster_monitor.db ".backup ~/cluster_monitor_backup.db"
```

### Clean Old Data

```bash
# Connect to database
sqlite3 ~/cluster_monitor.db

# Delete old records (keep last 90 days)
DELETE FROM node_status WHERE timestamp < datetime('now', '-90 days');
DELETE FROM node_events WHERE timestamp < datetime('now', '-90 days');
DELETE FROM recovery_attempts WHERE timestamp < datetime('now', '-90 days');

# Vacuum to reclaim space
VACUUM;
.quit
```

### View Cron Logs

```bash
# Real-time monitoring
tail -f ~/cluster_monitor_cron.log

# View last 100 lines
tail -100 ~/cluster_monitor_cron.log

# Search for errors
grep -i error ~/cluster_monitor_cron.log
```

## Example Workflows

### Daily Morning Check

```bash
# Check cluster health
./query_monitor_db.py --health

# Review any issues from last 24 hours
./query_monitor_db.py --problems --days 1

# Check specific problematic node
./query_monitor_db.py --node-detail spydur spdr05
```

### Weekly Review

```bash
# Generate comprehensive report
./cluster_node_monitor.py --report --days 7

# Check downtime statistics
./query_monitor_db.py --downtime --days 7

# Review recovery success rate
./query_monitor_db.py --recovery-stats --days 7
```

### Investigating Specific Node

```bash
# Get detailed node history
./query_monitor_db.py --node-detail spydur spdr12 --days 30

# Check current status
./query_monitor_db.py --current --cluster spydur

# Manual check via SSH
ssh installer@spydur 'sinfo -n spdr12'
```

## Advanced Usage

### Custom Recovery Commands

Edit `cluster_node_monitor.py` and modify the `CLUSTERS` dictionary:

```python
CLUSTERS = {
    'spydur': {
        'recovery_commands': [
            'scontrol update nodename={node} state=resume',
            'ssh {node} "sudo systemctl restart slurmd"',
            'ssh {node} "sudo reboot"',  # Add reboot as last resort
        ],
    }
}
```

### Change Monitoring Frequency

```bash
# Edit crontab
crontab -e

# Change from every 5 minutes (*/5) to every 10 minutes (*/10)
*/10 * * * * /path/to/cluster_node_monitor.py --monitor
```

### Disable Auto-Recovery

```bash
# Edit crontab
crontab -e

# Add --no-recovery flag
*/5 * * * * /path/to/cluster_node_monitor.py --monitor --no-recovery
```

## Security Considerations

- SSH keys should be properly secured (600 permissions)
- Database contains cluster status history (not highly sensitive)
- Email notifications may contain node names and states
- Recovery commands run with cluster management user privileges

## Support

For issues or questions:
1. Check logs: `~/cluster_monitor.log`
2. Verify configuration: `~/.config/cluster_monitor/config.toml`
3. Test components individually (SSH, SLURM commands, hpclib)

## License

Internal use for cluster management.

---

**Last Updated**: October 2025
**Version**: 1.0
**Maintainer**: cazuza@badenpowell
