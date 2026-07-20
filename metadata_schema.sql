-- ======================================================================
-- Central Metadata Repository Database Schema
-- Target Database: MySQL / MariaDB
-- ======================================================================

CREATE DATABASE IF NOT EXISTS METADATA_REPOSITORY_FRESH;
USE METADATA_REPOSITORY_FRESH;

-- ----------------------------------------------------------------------
-- 1. ETL Execution Logs Table
-- Stores execution statistics parsed from Hop logs.
-- ----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ETL_EXECUTION_LOG (
    execution_id INT AUTO_INCREMENT PRIMARY KEY,
    pipeline_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME NULL,
    duration_sec INT NULL,
    rows_read INT DEFAULT 0,
    rows_written INT DEFAULT 0,
    error_message TEXT NULL,
    raw_log LONGTEXT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_pipeline_start (pipeline_name, start_time),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------
-- 2. ETL Log Checkpoint Table
-- Tracks the last processed log timestamp for incremental collection.
-- ----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ETL_LOG_CHECKPOINT (
    collector_name VARCHAR(100) NOT NULL,
    pipeline_name VARCHAR(255) NOT NULL,
    last_processed_timestamp DATETIME NOT NULL,
    PRIMARY KEY (collector_name, pipeline_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------
-- 3. Source DB Metadata Table
-- Stores schema snapshots from the source database.
-- ----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS SOURCE_DB_METADATA (
    id INT AUTO_INCREMENT PRIMARY KEY,
    database_name VARCHAR(100) NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    column_name VARCHAR(100) NOT NULL,
    data_type VARCHAR(100) NOT NULL,
    is_nullable VARCHAR(10) NOT NULL,
    row_count BIGINT DEFAULT 0,
    last_updated DATETIME NULL,
    collected_at DATETIME NOT NULL,
    INDEX idx_src_table_collected (table_name, collected_at),
    INDEX idx_src_lookup (database_name, table_name, column_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------
-- 4. Target DB Metadata Table
-- Stores schema snapshots from the target database/data warehouse.
-- ----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS TARGET_DB_METADATA (
    id INT AUTO_INCREMENT PRIMARY KEY,
    database_name VARCHAR(100) NOT NULL,
    schema_name VARCHAR(100) NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    column_name VARCHAR(100) NOT NULL,
    data_type VARCHAR(100) NOT NULL,
    is_nullable VARCHAR(10) NOT NULL,
    row_count BIGINT DEFAULT 0,
    last_updated DATETIME NULL,
    collected_at DATETIME NOT NULL,
    INDEX idx_tgt_table_collected (table_name, collected_at),
    INDEX idx_tgt_lookup (database_name, schema_name, table_name, column_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
