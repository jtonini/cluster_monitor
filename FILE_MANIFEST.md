# Cluster Monitor File Manifest

Complete listing of all files in the cluster monitoring system, organized by purpose.

## Total Files: 19 (Standalone - No External Dependencies)

```
total 120K
-rw-r--r-- 1 cazuza cazuza 3.2K Oct 27 18:21 HPCLIB_DEPENDENCIES.md
-rw-r--r-- 1 cazuza cazuza 2.9K Oct 27 18:05 INSTALL.md
-rw-r--r-- 1 cazuza cazuza 1.1K Oct 27 18:21 LICENSE
-rw-r--r-- 1 cazuza cazuza  12K Oct 27 18:21 README.md
-rw-r--r-- 1 cazuza cazuza 6.5K Oct 27 18:21 cluster_monitor.toml
-rw-r--r-- 1 cazuza cazuza  19K Oct 27 18:21 cluster_monitor_dbclass.py
-rw-r--r-- 1 cazuza cazuza  14K Oct 27 18:21 cluster_monitor_functions.sh
-rw-r--r-- 1 cazuza cazuza 6.5K Oct 27 18:21 cluster_monitor_schema.sql
-rw-r--r-- 1 cazuza cazuza  27K Oct 27 18:05 cluster_node_monitor.py
-rw-r--r-- 1 cazuza cazuza 9.0K Oct 27 18:05 dashboard.sh
-rw-r--r-- 1 cazuza cazuza  15K Oct 27 18:05 query_monitor_db.py
-rw-r--r-- 1 cazuza cazuza 2.4K Oct 27 18:05 setup_cron.sh
```

---

## Core Application Files

### cluster_node_monitor.py (27KB)
**Purpose**: Main monitoring application
**Type**: Python script
**Dependencies**: hpclib (urdb, dorunrun, fname), cluster_monitor_dbclass
**Key Features**:
- Connects to spydur and arachne via SSH
- Checks SLURM node status using `sinfo`
- Detects problematic nodes
- Attempts automatic recovery
- Sends email notifications
- Logs all events to database

**Usage**:
```bash
./cluster_node_monitor.py --monitor          # Monitor with recovery
./cluster_node_monitor.py --monitor --no-recovery  # Check only
./cluster_node_monitor.py --report --days 7  # Generate report
```

---

### cluster_monitor_dbclass.py (19KB)
**Purpose**: Database operations class
**Type**: Python module
**Dependencies**: hpclib (urdb)
**Key Features**:
- Encapsulates all database operations
- Provides clean API for logging and queries
- Manages database schema initialization
- Includes built-in cleanup methods
- Handles batch operations efficiently

**Methods**:
- `log_node_status()` - Log single node status
- `log_node_status_batch()` - Log multiple statuses at once
- `log_event()` - Log node events
- `log_recovery_attempt()` - Log recovery attempts
- `get_latest_status()` - Query current status
- `get_problem_history()` - Get historical problems
- `cleanup_old_records()` - Database maintenance

---

### query_monitor_db.py (15KB)
**Purpose**: Database query and reporting tool
**Type**: Python script
**Dependencies**: hpclib (urdb, fname), cluster_monitor_dbclass
**Key Features**:
- Interactive database queries
- Multiple report formats
- Ad-hoc analysis capabilities
- Node-specific details
- Historical trend analysis

**Usage**:
```bash
./query_monitor_db.py --health              # Cluster health
./query_monitor_db.py --current             # Current status
./query_monitor_db.py --problems --days 7   # Problem history
./query_monitor_db.py --recovery-stats      # Recovery stats
./query_monitor_db.py --node-detail spydur spdr01  # Node details
```

---

## HPC Library Files (Included in Repository)

### urdb.py (2.2KB)
**Purpose**: Universal Relational Database wrapper
**Type**: Python module (from hpclib)
**Dependencies**: Python sqlite3
**Key Features**:
- Simplified SQLite interface
- Automatic connection management
- Context manager support
- Used by all database operations

**Key Methods**:
- `execute(query, params)` - Execute SQL
- `fetchall()` - Get all results
- `fetchone()` - Get one result

### dorunrun.py (4.6KB)
**Purpose**: Command execution wrapper
**Type**: Python module (from hpclib)
**Dependencies**: Python subprocess
**Key Features**:
- Safe command execution
- Stdout/stderr capture
- Timeout support
- Result object with .OK property
- Type conversion

**Usage Example**:
```python
from dorunrun import dorunrun

result = dorunrun("sinfo -h", return_datatype=str)
if result.OK:
    print(result.stdout)
```

### fname.py (2.4KB)
**Purpose**: Filename and path utilities
**Type**: Python module (from hpclib)
**Dependencies**: Python pathlib
**Key Features**:
- Filename component extraction
- Path manipulation
- Script name detection

**Usage Example**:
```python
import fname

script_name = fname.Fname(__file__)
print(script_name.stem)  # Name without extension
```

**Note:** These three files make the project completely standalone with no external hpclib dependency required.

---

## Configuration Files

### cluster_monitor.toml (6.5KB)
**Purpose**: Main configuration file
**Type**: TOML configuration
**Location**: Copy to `~/.config/cluster_monitor/config.toml`
**Sections**:
- `[email]` - Email notification settings
- `[spydur]` - Spydur cluster configuration
- `[arachne]` - Arachne cluster configuration
- `[monitoring]` - Monitoring behavior settings
- `[database]` - Database configuration
- `[logging]` - Logging configuration
- `[reporting]` - Report generation settings
- `[advanced]` - Advanced options

**Key Settings**:
```toml
[email]
to = ["your-email@domain.com"]  # Update this!

[monitoring]
check_interval = 300  # 5 minutes
max_recovery_attempts = 3

[database]
retention_days = 90
```

---

### cluster_monitor_schema.sql (6.5KB)
**Purpose**: SQL database schema
**Type**: SQL DDL
**Tables**:
- `node_status` - Status check history
- `node_events` - Event log
- `recovery_attempts` - Recovery attempts log

**Views**:
- `latest_node_status` - Current node status
- `current_problems` - Nodes with problems
- `cluster_health_summary` - Health statistics
- `recent_events` - Last 24 hours of events
- `recovery_success_rate` - Recovery statistics

**Indexes**: Optimized for timestamp and cluster/node queries

---

## Shell Utilities

### cluster_monitor_functions.sh (14KB)
**Purpose**: Bash utility functions
**Type**: Bash functions library
**Usage**: `source cluster_monitor_functions.sh`

**Function Categories**:
1. **Connection Functions**
   - `check_cluster_connection` - Test SSH
   - `get_node_status` - Get SLURM status
   - `is_node_up` - Check specific node

2. **Monitoring Functions**
   - `run_monitor` - Full monitoring check
   - `check_only` - Status check only
   - `check_cluster` - Check specific cluster

3. **Query Functions**
   - `cluster_health` - Health summary
   - `current_status` - Current status
   - `problem_history` - Problem history
   - `recovery_stats` - Recovery statistics
   - `node_details` - Node-specific details

4. **Database Functions**
   - `db_stats` - Database statistics
   - `db_cleanup` - Cleanup old records
   - `db_backup` - Backup database
   - `db_query` - Execute SQL

5. **Utility Functions**
   - `watch_clusters` - Auto-refresh dashboard
   - `alert_if_problems` - Alert on problems
   - `quick_check` - Quick health check

6. **Recovery Functions**
   - `resume_node` - Manually resume node
   - `restart_slurmd` - Restart slurmd service

**Examples**:
```bash
source cluster_monitor_functions.sh
cluster_health
problem_history 7 spydur
watch_clusters 30
```

---

### dashboard.sh (9.0KB)
**Purpose**: Interactive status dashboard
**Type**: Bash script
**Features**:
- Color-coded output
- Real-time cluster status
- Recent issues summary
- Recovery statistics
- System status
- Can auto-refresh

**Usage**:
```bash
./dashboard.sh        # Show dashboard once
# Edit script to enable auto-refresh
```

---

### setup_cron.sh (2.4KB)
**Purpose**: Automated cron job installer
**Type**: Bash script
**Features**:
- Installs monitoring cron jobs
- Backs up existing crontab
- Configures daily/weekly reports
- Makes scripts executable

**Installed Jobs**:
- Monitor clusters every 5 minutes
- Daily report at 8 AM
- Weekly report every Monday at 8 AM

**Usage**:
```bash
./setup_cron.sh
# View installed jobs
crontab -l
```

---

## Documentation Files

### README.md (12KB)
**Purpose**: Comprehensive documentation
**Sections**:
- Overview and architecture
- Installation instructions
- Usage examples
- Configuration guide
- Database schema
- Troubleshooting
- Maintenance procedures
- Advanced usage

**Audience**: Primary reference for all users

---

### INSTALL.md (2.9KB)
**Purpose**: Quick start installation guide
**Type**: Step-by-step guide
**Features**:
- Prerequisites checklist
- 5-minute installation
- Verification steps
- Common issues
- Quick reference

**Audience**: New users and initial setup

---

### HPCLIB_DEPENDENCIES.md (3.2KB)
**Purpose**: hpclib requirements documentation
**Type**: Dependency guide
**Contents**:
- Required hpclib modules
- Optional modules
- Installation instructions
- Verification steps
- Troubleshooting
- Alternative configurations

**Audience**: System administrators and troubleshooting

---

### LICENSE (1.1KB)
**Purpose**: Software license
**Type**: MIT License
**Terms**: Open source, free to use and modify

---

## File Dependencies

```
cluster_node_monitor.py
+-- cluster_monitor_dbclass.py
|   \-- urdb.py (hpclib)
+-- dorunrun.py (hpclib)
+-- fname.py (hpclib)
\-- cluster_monitor.toml

query_monitor_db.py
+-- cluster_monitor_dbclass.py
|   \-- urdb.py (hpclib)
\-- fname.py (hpclib)

cluster_monitor_functions.sh
+-- cluster_node_monitor.py
+-- query_monitor_db.py
\-- cluster_monitor.db

dashboard.sh
+-- cluster_monitor_functions.sh
\-- cluster_monitor.db

setup_cron.sh
\-- cluster_node_monitor.py
```

---

## Generated Files (Not in Repository)

These files are created during operation:

### ~/.config/cluster_monitor/config.toml
- Created on first run from cluster_monitor.toml template
- User-customized configuration

### ~/cluster_monitor.db
- SQLite database
- Created automatically on first run
- Stores all monitoring data

### ~/cluster_monitor.log
- Main application log
- Rotates when large

### ~/cluster_monitor_cron.log
- Cron job execution log
- Shows automated run results

---

## Comparison with NAS Monitoring Project

Similar structure to the NAS mounting automation project:

| Feature | NAS Project | Cluster Monitor |
|---------|-------------|-----------------|
| Main script | nas_monitor.py | cluster_node_monitor.py |
| DB class | nas_monitor_dbclass.py | cluster_monitor_dbclass.py |
| Schema | nas_monitor_schema.sql | cluster_monitor_schema.sql |
| Config | nas_monitor.toml | cluster_monitor.toml |
| Query tool | nas_query.py | query_monitor_db.py |
| Functions | nas_functions.sh | cluster_monitor_functions.sh |
| hpclib deps | dorunrun, urdb, etc. | dorunrun, urdb, fname |

Both projects follow the same architectural patterns and coding standards.

---

## Quick Reference

**Start monitoring**:
```bash
source cluster_monitor_functions.sh
run_monitor
```

**Check status**:
```bash
cluster_health
current_status
```

**View problems**:
```bash
problem_history 7
```

**Manual recovery**:
```bash
resume_node spydur spdr05
```

**Generate report**:
```bash
generate_report 7
```

---

**Last Updated**: October 27, 2025
**Version**: 1.0
**Repository**: ~/cluster_monitor/
