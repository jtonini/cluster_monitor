-- Cluster Node Monitor Database Schema
-- SQLite database for tracking cluster node status and events

-- ============================================================================
-- Table: node_status
-- Purpose: Records every node status check performed
-- ============================================================================
CREATE TABLE IF NOT EXISTS node_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,           -- ISO format timestamp
    cluster TEXT NOT NULL,             -- Cluster name (spydur, arachne)
    node_name TEXT NOT NULL,           -- Node hostname
    status TEXT NOT NULL,              -- 'ok' or 'problem'
    slurm_state TEXT,                  -- SLURM state string (idle, down, drain, etc.)
    is_available BOOLEAN NOT NULL,     -- 1 if available, 0 if problem
    checked_from TEXT NOT NULL         -- Hostname that performed the check
);

-- ============================================================================
-- Table: node_events
-- Purpose: Records significant node events (problems, recoveries, etc.)
-- ============================================================================
CREATE TABLE IF NOT EXISTS node_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,           -- ISO format timestamp
    cluster TEXT NOT NULL,             -- Cluster name
    node_name TEXT NOT NULL,           -- Node hostname
    event_type TEXT NOT NULL,          -- Type: node_down, recovery_started, etc.
    details TEXT,                      -- Detailed description
    severity TEXT NOT NULL             -- info, warning, error, critical
);

-- ============================================================================
-- Table: recovery_attempts
-- Purpose: Records all node recovery attempts and their outcomes
-- ============================================================================
CREATE TABLE IF NOT EXISTS recovery_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,           -- ISO format timestamp
    cluster TEXT NOT NULL,             -- Cluster name
    node_name TEXT NOT NULL,           -- Node hostname
    command TEXT NOT NULL,             -- Command that was executed
    exit_code INTEGER,                 -- Command exit code
    output TEXT,                       -- Command output/error
    success BOOLEAN NOT NULL           -- 1 if successful, 0 if failed
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

-- Indexes for node_status table
CREATE INDEX IF NOT EXISTS idx_node_status_timestamp 
    ON node_status(timestamp);

CREATE INDEX IF NOT EXISTS idx_node_status_cluster_node 
    ON node_status(cluster, node_name);

CREATE INDEX IF NOT EXISTS idx_node_status_available 
    ON node_status(is_available);

-- Indexes for node_events table
CREATE INDEX IF NOT EXISTS idx_node_events_timestamp 
    ON node_events(timestamp);

CREATE INDEX IF NOT EXISTS idx_node_events_cluster_node 
    ON node_events(cluster, node_name);

CREATE INDEX IF NOT EXISTS idx_node_events_severity 
    ON node_events(severity);

CREATE INDEX IF NOT EXISTS idx_node_events_type 
    ON node_events(event_type);

-- Indexes for recovery_attempts table
CREATE INDEX IF NOT EXISTS idx_recovery_timestamp 
    ON recovery_attempts(timestamp);

CREATE INDEX IF NOT EXISTS idx_recovery_cluster_node 
    ON recovery_attempts(cluster, node_name);

CREATE INDEX IF NOT EXISTS idx_recovery_success 
    ON recovery_attempts(success);

-- ============================================================================
-- Views for Common Queries
-- ============================================================================

-- View: latest_node_status
-- Shows the most recent status for all nodes
CREATE VIEW IF NOT EXISTS latest_node_status AS
SELECT 
    ns.cluster,
    ns.node_name,
    ns.slurm_state,
    ns.is_available,
    ns.timestamp,
    ns.checked_from
FROM node_status ns
INNER JOIN (
    SELECT cluster, node_name, MAX(timestamp) as max_timestamp
    FROM node_status
    GROUP BY cluster, node_name
) latest ON ns.cluster = latest.cluster 
    AND ns.node_name = latest.node_name 
    AND ns.timestamp = latest.max_timestamp;

-- View: current_problems
-- Shows nodes currently in problem state
CREATE VIEW IF NOT EXISTS current_problems AS
SELECT 
    cluster,
    node_name,
    slurm_state,
    timestamp
FROM latest_node_status
WHERE is_available = 0
ORDER BY cluster, node_name;

-- View: cluster_health_summary
-- Provides health statistics per cluster
CREATE VIEW IF NOT EXISTS cluster_health_summary AS
SELECT 
    cluster,
    COUNT(*) as total_nodes,
    SUM(CASE WHEN is_available = 1 THEN 1 ELSE 0 END) as healthy_nodes,
    SUM(CASE WHEN is_available = 0 THEN 1 ELSE 0 END) as problem_nodes,
    ROUND(SUM(CASE WHEN is_available = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as health_percentage,
    MAX(timestamp) as last_check
FROM latest_node_status
GROUP BY cluster;

-- View: recent_events
-- Shows events from the last 24 hours
CREATE VIEW IF NOT EXISTS recent_events AS
SELECT 
    timestamp,
    cluster,
    node_name,
    event_type,
    details,
    severity
FROM node_events
WHERE timestamp > datetime('now', '-1 day')
ORDER BY timestamp DESC;

-- View: recovery_success_rate
-- Shows recovery success rates per cluster
CREATE VIEW IF NOT EXISTS recovery_success_rate AS
SELECT 
    cluster,
    COUNT(*) as total_attempts,
    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed,
    ROUND(SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as success_rate
FROM recovery_attempts
WHERE timestamp > datetime('now', '-7 days')
GROUP BY cluster;

-- ============================================================================
-- Maintenance Queries
-- ============================================================================

-- To clean old records (adjust date as needed):
-- DELETE FROM node_status WHERE timestamp < datetime('now', '-90 days');
-- DELETE FROM node_events WHERE timestamp < datetime('now', '-90 days');
-- DELETE FROM recovery_attempts WHERE timestamp < datetime('now', '-90 days');
-- VACUUM;

-- To get database size:
-- SELECT page_count * page_size / 1024.0 / 1024.0 AS size_mb FROM pragma_page_count(), pragma_page_size();

-- To check table sizes:
-- SELECT name, SUM(pgsize) / 1024.0 / 1024.0 AS size_mb FROM dbstat GROUP BY name ORDER BY size_mb DESC;
