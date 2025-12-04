# Changelog

## Version 1.2 - Queue Analysis Feature (December 2024)

### New Features
- **Job Queue Analyzer**: Detect misleading SLURM job status messages
  - Identifies jobs showing "nodes DOWN/DRAINED" when nodes are actually available
  - Reports real reason: CPUs exhausted, GPUs allocated, memory full, etc.
  - Helps users understand why jobs are really waiting
- **check_queue.py**: Standalone tool for quick queue analysis
- **Bash functions**: Added `check_queue` and `check_queue_verbose` commands

### Files Added
- job_queue_analyzer.py - Core queue analysis engine (372 lines)
- check_queue.py - Command-line queue checker (118 lines)

### Use Cases
- Job appears stuck with "nodes DOWN" but nodes are actually online
- Users confused about why jobs won't start
- Admins want to identify resource bottlenecks quickly
- Distinguish between actual node failures and resource exhaustion

### Usage
```bash
# Check all clusters
./check_queue.py

# Check specific cluster
./check_queue.py --cluster spydur

# Verbose output with details
./check_queue.py --verbose

# Via bash function
source cluster_monitor_functions.sh
check_queue
```

# Changelog

## Version 1.1 - Production Ready (December 2024)

### Bug Fixes
- **Fixed query_monitor_db.py**: SQL query now correctly shows all clusters (was only showing cluster with most recent timestamp)
- **Fixed node_details**: Corrected column names (command/output instead of recovery_action/error_message)
- **Fixed get_node_status**: Removed duplicates by using `sort -u` (nodes were appearing once per partition)
- **Fixed monitor_help**: Removed escape sequences causing formatting issues

### Enhancements
- **Added node_info function**: Show live SLURM node details (CPU, memory, GPU, running jobs)
- **Email alias support**: Documentation for using local aliases to forward external emails
- **Generic documentation**: All docs now use generic placeholders instead of specific hostnames

### Documentation
- **Created SETUP_NOTES.md**: Post-installation configuration guide
- **Created CHANGELOG.md**: Consolidated change history
- **Updated README.md**: Removed hardcoded hostnames/usernames
- **Updated INSTALL.md**: Generic installation instructions

## Version 1.0 - Initial Release (November 2024)

### Features
- Automated monitoring of SLURM cluster nodes (30-second checks)
- Automatic recovery of failed nodes (resume + restart slurmd)
- NOT_RESPONDING detection (idle* states with asterisk)
- SQLite database logging with retention policies
- Email notifications with configurable severity levels
- 25+ bash utility functions for cluster management
- Interactive status dashboard
- Multiple query and reporting tools
- Cron-based automation (5-minute intervals)

### Cluster Support
- Supports multiple SLURM clusters simultaneously
- Cluster-specific sudo configurations
- Per-cluster SSH user management
- Configurable recovery commands per cluster

### Architecture
- Python 3.8+ required
- Standalone repository (all dependencies included)
- No external packages except tomllib/tomli
- Clean separation of concerns (monitor, database, query)

### Configuration Updates

#### Sudo Access Configuration
Cluster-specific recovery commands based on access patterns:

**Pattern 1: Limited sudo with user impersonation**
- Resume node: `sudo -u slurm scontrol update nodename=NODE state=resume`
- Restart daemon: `ssh NODE "sudo systemctl restart slurmd"`
- Use case: Management user with NOPASSWD for specific systemctl commands

**Pattern 2: Full sudo or root access**
- Resume node: `sudo scontrol update nodename=NODE state=resume`
- Restart daemon: `ssh NODE "systemctl restart slurmd"`
- Use case: Management user in wheel group or logs in as root to nodes

#### Files Included
**Core Application (3 files, 64KB):**
- cluster_node_monitor.py - Main monitoring script
- cluster_monitor_dbclass.py - Database operations
- query_monitor_db.py - Query and reporting tool

**HPC Library (7 files, 23KB):**
- dorunrun.py - Command execution wrapper
- urdb.py - Database wrapper
- fname.py - Filename utilities
- sqlitedb.py - Extended SQLite operations
- urdecorators.py - Utility decorators
- urlogger.py - Logging utilities
- linuxutils.py - Linux system utilities

**Configuration (2 files):**
- cluster_monitor.toml - TOML configuration
- cluster_monitor_schema.sql - Database schema

**Shell Utilities (3 files):**
- cluster_monitor_functions.sh - 25+ bash functions
- dashboard.sh - Interactive status dashboard
- setup_cron.sh - Cron job installer

**Documentation (7 files):**
- README.md - Main documentation
- INSTALL.md - Quick start guide
- SETUP_NOTES.md - Post-installation configuration
- FINAL_CONFIGURATION.md - Sudo command reference
- FILE_MANIFEST.md - Complete file listing
- HPCLIB_DEPENDENCIES.md - Library documentation
- CHANGELOG.md - This file

### Database Schema
**Tables:**
- node_status - Current state of all nodes
- node_events - Historical events log
- recovery_attempts - Recovery action history

**Views:**
- current_status - Latest status per node
- problem_nodes - Nodes with issues
- recovery_success_rate - Statistics
- downtime_summary - Availability metrics
- node_event_history - Complete audit trail

### Known Limitations
- Requires passwordless SSH to cluster head nodes
- Postfix or equivalent MTA required for email notifications
- Cannot send external emails without mail relay or aliases
- SLURM-specific (not compatible with other schedulers)

### Security Considerations
- Uses SSH keys for authentication
- Requires sudo privileges for recovery operations
- All commands logged to database
- Email may contain node names and states

---

## Future Enhancements (Not Yet Implemented)

- Queue analysis for misleading job statuses (GPU exhaustion detection)
- Web-based dashboard interface
- Slack/Teams integration
- Grafana integration for metrics
- API endpoint for external monitoring
- Multi-site cluster support
