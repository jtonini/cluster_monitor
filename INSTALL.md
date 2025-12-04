# Quick Start Installation Guide

## Prerequisites

### System Requirements

**Control Host:**
- Linux system with Python 3.8 or higher
- Passwordless SSH access to cluster head nodes
- Sudo access for postfix configuration
- Disk space: ~50MB for application + database growth

**Cluster Requirements:**
- SLURM workload manager installed
- SSH access with management credentials
- Sudo privileges for recovery operations (configurable per cluster)

### Pre-Installation Checks
```bash
# 1. Verify Python version (need 3.8+)
python3 --version

# 2. Test SSH connectivity to cluster head nodes
ssh <management-user>@<cluster-head-node> hostname

# 3. Test SLURM commands
ssh <management-user>@<cluster-head-node> 'sinfo -h -N -o "%N %T"'

# 4. Check sudo access (if recovery will be automated)
ssh <management-user>@<cluster-head-node> 'sudo -l'
```

If all checks pass, proceed to installation.

---

## Installation (5-10 minutes)

### Step 1: Create Installation Directory
```bash
# Choose installation location
mkdir -p ~/cluster_monitor
cd ~/cluster_monitor
```

### Step 2: Copy Repository Files

Copy all files to the installation directory:

**Required Core Files:**
- cluster_node_monitor.py
- cluster_monitor_dbclass.py
- query_monitor_db.py
- cluster_monitor.toml
- cluster_monitor_schema.sql

**Required HPC Library Files:**
- dorunrun.py
- urdb.py
- fname.py
- sqlitedb.py
- urdecorators.py
- urlogger.py
- linuxutils.py

**Shell Utilities:**
- cluster_monitor_functions.sh
- dashboard.sh
- setup_cron.sh

**Documentation:**
- All .md files (optional but recommended)

### Step 3: Make Scripts Executable
```bash
chmod +x *.py *.sh
```

### Step 4: Initial Configuration

Run the monitor once to create the default configuration:
```bash
./cluster_node_monitor.py --monitor --no-recovery
```

This creates:
- `~/.config/cluster_monitor/config.toml` - Configuration file
- `~/cluster_monitor.db` - SQLite database
- `~/cluster_monitor.log` - Log file

### Step 5: Edit Configuration
```bash
vim ~/.config/cluster_monitor/config.toml
```

**Update these sections:**
```toml
# Email settings (use local aliases - see SETUP_NOTES.md)
[email]
enabled = true
from = "monitoring@your-control-host"
to = ["monitoring-alias"]     # Local alias that forwards to your email
cc = []
smtp_server = "localhost"
smtp_port = 25

# Configure your clusters
[cluster1]
head_node = "cluster1-head.domain.com"
user = "management-user"
nodes = ["node01", "node02", "node03"]  # Or use ["node[01-10]"] for ranges
problem_states = ["down", "drain", "fail", "maint", "unk"]

[cluster2]
head_node = "cluster2-head.domain.com"
user = "management-user"
nodes = ["compute01", "compute02"]
problem_states = ["down", "drain", "fail", "maint", "unk"]
```

**Important:** See [SETUP_NOTES.md](SETUP_NOTES.md) for email configuration details.

### Step 6: Test Monitoring
```bash
# Test without recovery (safe)
./cluster_node_monitor.py --monitor --no-recovery

# Check the output - should show all nodes
./query_monitor_db.py --current

# View health summary
./query_monitor_db.py --health
```

### Step 7: Configure Automated Monitoring
```bash
# Install cron jobs
./setup_cron.sh
```

This installs:
- Monitoring every 5 minutes with auto-recovery
- Daily report at 8:00 AM
- Weekly report every Monday at 8:00 AM

**Verify cron installation:**
```bash
crontab -l | grep cluster_monitor
```

---

## Post-Installation Setup

### Email Configuration (CRITICAL)

Most systems cannot send external emails directly. Set up local aliases:

**See [SETUP_NOTES.md](SETUP_NOTES.md) for complete instructions.**

Quick summary:
1. Create aliases in `/etc/aliases`
2. Rebuild with `sudo newaliases`
3. Enable postfix: `sudo systemctl enable --now postfix`
4. Test delivery

### Load Bash Functions (Optional)

Add to your `~/.bashrc`:
```bash
# Cluster monitoring functions
if [ -f ~/cluster_monitor/cluster_monitor_functions.sh ]; then
    source ~/cluster_monitor/cluster_monitor_functions.sh
fi
```

Then reload: `source ~/.bashrc`

**Available functions:**
```bash
monitor_help           # Show all available functions
cluster_health         # Quick cluster overview
current_status         # Current node status
node_info <cluster> <node>    # Live node details
problem_history 7      # Last 7 days of problems
watch_clusters 30      # Auto-refresh every 30 seconds
```

---

## Verification

### Check Everything is Working
```bash
# 1. Database created
ls -lh ~/cluster_monitor.db

# 2. Log file has entries
tail ~/cluster_monitor.log

# 3. Current status shows all clusters
./query_monitor_db.py --current

# 4. Cron is scheduled
crontab -l | grep cluster_monitor

# 5. Email can be sent
echo "Test" | mail -s "Test" <your-alias>
```

### Expected Output

When running `./query_monitor_db.py --current`, you should see:
```
============================================================
CURRENT NODE STATUS
============================================================
cluster1 (as of 2024-12-04T10:00:00):
  [OK] node01        mixed
  [OK] node02        idle
  [OK] node03        allocated
  Summary: 3 healthy, 0 problem

cluster2 (as of 2024-12-04T10:00:05):
  [OK] compute01     mixed
  [OK] compute02     idle
  Summary: 2 healthy, 0 problem
```

---

## Troubleshooting

### Installation Issues

**Python version too old:**
```bash
python3 --version
# Must be 3.8 or higher
```

**SSH connection fails:**
```bash
# Test SSH keys
ssh <user>@<cluster-head> hostname
# If fails, set up SSH keys:
ssh-keygen
ssh-copy-id <user>@<cluster-head>
```

**Import errors:**
```bash
# Verify all files are present
ls -1 *.py | wc -l
# Should be 10 Python files
```

### Configuration Issues

**No clusters showing:**
- Check `~/.config/cluster_monitor/config.toml` syntax
- Verify cluster names match in TOML file
- Check SSH access to head nodes

**Database errors:**
```bash
# Reinitialize database
rm ~/cluster_monitor.db
./cluster_node_monitor.py --monitor --no-recovery
```

**Email not working:**
- See [SETUP_NOTES.md](SETUP_NOTES.md) for email configuration
- Check postfix is running: `systemctl status postfix`
- Verify aliases are configured: `cat /etc/aliases`

---

## Next Steps

After installation:

1. **Configure email properly** - See [SETUP_NOTES.md](SETUP_NOTES.md)
2. **Customize recovery commands** - See [FINAL_CONFIGURATION.md](FINAL_CONFIGURATION.md)
3. **Test recovery on non-production node** - Verify sudo permissions work
4. **Monitor for a few days** - Watch logs and verify notifications
5. **Adjust retention policies** - Edit config.toml if needed

---

## Support

- **Setup issues:** See [SETUP_NOTES.md](SETUP_NOTES.md)
- **Command reference:** See [FINAL_CONFIGURATION.md](FINAL_CONFIGURATION.md)
- **File descriptions:** See [FILE_MANIFEST.md](FILE_MANIFEST.md)
- **All changes:** See [CHANGELOG.md](CHANGELOG.md)

---

**Installation complete!** The system is now monitoring your clusters every 5 minutes.
