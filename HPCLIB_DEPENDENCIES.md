# HPC Library Dependencies - INCLUDED IN REPOSITORY

This cluster monitoring system includes all required hpclib modules directly in the repository for **standalone operation**.

## NO EXTERNAL INSTALLATION REQUIRED

All hpclib modules are included. You do NOT need to:
- Clone the hpclib repository separately
- Install hpclib from GitHub  
- Set up any sys.path modifications

## Included Modules (7 files)

### Required for Core Functionality

1. **urdb.py** (3.5KB)
   - Universal Database wrapper for SQLite operations
   - Provides clean interface with connection management
   - Used by: cluster_monitor_dbclass.py, query_monitor_db.py

2. **dorunrun.py** (3.4KB)
   - Command execution wrapper with structured results
   - Returns ExitCode namedtuple (OK, exit_code, value, stdout, stderr)
   - Used by: cluster_node_monitor.py

3. **fname.py** (2.2KB)
   - Filename and path utilities
   - Script name, directory, extension parsing
   - Used by: All main scripts

### Additional Utilities (Available but Optional)

4. **sqlitedb.py** (2.4KB)
   - Extended SQLite operations
   - Backup, vacuum, analyze, size checking
   - Available for advanced database operations

5. **urdecorators.py** (2.9KB)
   - Function decorators (timer, retry, memoize, etc.)
   - Available for performance monitoring

6. **urlogger.py** (2.7KB)
   - Enhanced logging utilities
   - Easy logger setup with file and console handlers
   - Available for custom logging needs

7. **linuxutils.py** (3.2KB)
   - Linux system utilities
   - User/system info, file operations, disk usage
   - Available for system monitoring tasks

## Repository Structure

```
cluster_monitor/
+-- cluster_node_monitor.py      Main monitoring script
+-- cluster_monitor_dbclass.py   Database operations class
+-- query_monitor_db.py           Query and reporting tool
+-- cluster_monitor_functions.sh  Bash utilities
+-- dashboard.sh                  Status dashboard
+-- setup_cron.sh                 Cron installer
|
+-- urdb.py                       hpclib - Database wrapper
+-- dorunrun.py                   hpclib - Command execution
+-- fname.py                      hpclib - Filename utilities
+-- sqlitedb.py                   hpclib - Extended SQLite
+-- urdecorators.py               hpclib - Decorators
+-- urlogger.py                   hpclib - Logging
+-- linuxutils.py                 hpclib - System utilities
|
+-- cluster_monitor.toml          Config template
+-- cluster_monitor_schema.sql    Database schema
+-- README.md                     Documentation
+-- (other docs...)
```

## Automatic Imports

The scripts automatically import from the local directory:

```python
# In cluster_node_monitor.py
from urdb import URdb
from dorunrun import dorunrun
import fname

# No sys.path manipulation needed!
```

## Verification

Test that all modules import correctly:

```bash
cd ~/cluster_monitor

# Test imports
python3 << 'EOF'
from urdb import URdb
from dorunrun import dorunrun
import fname
import sqlitedb
import urdecorators
import urlogger
import linuxutils
print("All hpclib modules imported successfully!")
EOF
```

## Module Details

### urdb.py - Database Wrapper

```python
from urdb import URdb

# Create database connection
db = URdb('cluster_monitor.db')

# Execute queries
db.execute("CREATE TABLE test (id INTEGER, name TEXT)")
db.execute("INSERT INTO test VALUES (?, ?)", (1, "Test"))

# Fetch results
rows = db.execute("SELECT * FROM test").fetchall()

# Auto-commit for non-SELECT queries
db.close()
```

**Key Features:**
- Connection management
- Parameter binding (SQL injection protection)
- Auto-commit for INSERT/UPDATE/DELETE
- Row dictionary access
- Utility methods: table_exists(), get_tables(), get_columns()

### dorunrun.py - Command Execution

```python
from dorunrun import dorunrun

# Execute command
result = dorunrun("sinfo -h -N -o '%N %T'")

# Check result
if result.OK:
    print(f"Success: {result.value}")
else:
    print(f"Failed: {result.stderr}")

# Access all fields
print(f"Exit code: {result.exit_code}")
print(f"Stdout: {result.stdout}")
print(f"Stderr: {result.stderr}")
```

**Key Features:**
- Returns structured ExitCode namedtuple
- Timeout support
- Type conversion (str, list, int, etc.)
- Input data support
- Exception handling

### fname.py - Filename Utilities

```python
import fname

# Get script info
f = fname.Fname(__file__)
print(f.basename)      # Script name without extension
print(f.directory)     # Script directory
print(f.extension)     # File extension
print(f.fullpath)      # Full absolute path

# Create related paths
log_file = f.with_extension('.log')
backup = f.with_suffix('_backup')
config = f.sibling('config.toml')
```

**Key Features:**
- Path parsing and manipulation
- Extension handling
- Sibling file paths
- Existence checking

## Advantages of Included Modules

1. **Standalone** - No external dependencies
2. **Portable** - Copy entire directory and it works
3. **Version controlled** - All dependencies tracked in git
4. **No conflicts** - Isolated from system hpclib
5. **Simplified deployment** - One directory to copy

## Original Source

These modules are derived from:
**https://github.com/georgeflanagin/hpclib**

Included here for convenience and standalone operation.

## Comparison with NAS Monitor

Your NAS monitor project includes the same approach:

```
/NAS_mount/
+-- nas_monitor.py
+-- nas_monitor_dbclass.py
+-- nas_query.py
+-- dorunrun.py          # Included
+-- linuxutils.py        # Included
+-- sqlitedb.py          # Included
+-- urdecorators.py      # Included
+-- urlogger.py          # Included
\-- nas_functions.sh
```

The cluster monitor follows the same pattern for consistency.

## No Installation Steps

Because the modules are included, the installation process is simpler:

```bash
# Just copy the directory
scp -r cluster_monitor cazuza@badenpowell:~/

# Make scripts executable
cd ~/cluster_monitor
chmod +x *.py *.sh

# Run
./cluster_node_monitor.py --monitor
```

That's it! No hpclib installation required.
