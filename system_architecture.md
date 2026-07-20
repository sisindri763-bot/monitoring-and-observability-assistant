# ETL Observability & AI Monitoring Platform: System Architecture Blueprint

This document details the complete end-to-end architecture of the ETL Observability system. It maps all components, directories, and code files, outlining their exact functionalities and data flows.

---

## 🏗️ 1. High-Level Architecture Diagram

The system operates as a continuous pipeline log ingestion and metadata monitoring network:

```mermaid
graph TD
    %% Source & Targets
    MySQL_Src[(Source DB: MySQL)] -->|Monitored by| Src_Coll[Source Metadata Collector]
    SF_Tgt[(Target DB: Snowflake)] -->|Monitored by| Tgt_Coll[Target Metadata Collector]
    
    %% Apache Hop Logging
    Hop[Apache Hop Pipelines] -->|Write logs to| Hop_Log[hopui.log]
    Hop_Log -->|Parsed by| Log_Coll[ETL Log Ingestor Collector]

    %% Daemon service
    Monitor_Svc[ETL Monitor Service: Windows Daemon] -->|Triggers every 30s| Src_Coll
    Monitor_Svc -->|Triggers every 30s| Tgt_Coll
    Monitor_Svc -->|Triggers every 30s| Log_Coll

    %% Telemetry Repository
    Src_Coll -->|Writes updates| Meta_Repo[(Central MySQL Repository)]
    Tgt_Coll -->|Writes updates| Meta_Repo
    Log_Coll -->|Writes runs metrics| Meta_Repo

    %% Alerts & Notifications
    Log_Coll -->|If status = FAILED| Email_Router[SMTP Email Dispatcher]
    Log_Coll -->|If status = FAILED| Webhook_Router[Webhook Alerts Dispatcher]
    Email_Router -->|Sends masked alert| Admin_Email([sm2178960@gmail.com])
    Webhook_Router -->|Sends payload| Slack_Teams([Slack/MS Teams channels])

    %% FastAPI Backend & AI
    API_Backend[FastAPI Observability Server] -->|Queries telemetry stats| Meta_Repo
    API_Backend -->|Queries context| OpenRouter[OpenRouter AI completions: Llama/Gemini]
    
    %% User Endpoints
    User_CLI[test_agents_console.py] -->|Queries APIs| API_Backend
    User_Dashboard[Frontend Dashboard UI] -->|Visualizes data| API_Backend
```

---

## 🗄️ 2. Central MySQL Repository Schema
All telemetry data is logged in a centralized database schema:
1. `ETL_EXECUTION_LOG`: Tracks pipeline execution statuses, start/end timestamps, logs, rows processed, and failures.
2. `ETL_LOG_CHECKPOINT`: Tracks the last processed log time per pipeline to prevent duplicate parsing.
3. `SOURCE_DB_METADATA`: Stores table name, row count, columns count, and last altered time of the source MySQL DB.
4. `TARGET_DB_METADATA`: Stores table name, row count, columns count, and last altered time of target Snowflake DB.
5. `ALERT_WEBHOOKS`: Registers Slack, MS Teams, or Discord active alert receiver webhook URLs.

---

## 📂 3. Directory & File Blueprint

### ⚙️ Root Directory Configurations
* [.env](file:///d:/projects/.env): Single unified configuration file mapping keys, database hosts, alerts configs, and collector executables.
* [metadata_schema.sql](file:///d:/projects/metadata_schema.sql): Telemetry database table definitions.
* [system_architecture.md](file:///d:/projects/system_architecture.md): This architectural mapping document.

---

### 1. 📥 Component A: ETL Log Ingestor (`etl_log_collector`)
Reads, cleans, and ingests execution logs written by Apache Hop.
* [main.py](file:///d:/projects/etl_log_collector/main.py): Entrypoint to parse logs.
* [collector.py](file:///d:/projects/etl_log_collector/collector.py):
  * Reads `hopui.log`.
  * Splits log entries by pipeline execution runs.
  * Detects status (`SUCCESS` vs `FAILED`).
  * Extracts failure messages and filters database credentials and hostnames.
  * Dispatches SMTP plain-text notifications and JSON webhook payloads on failure.
* [database.py](file:///d:/projects/etl_log_collector/database.py): MySQL DB connector. Houses the centralized `mask_sensitive_data(text)` utility.
* [checkpoint.py](file:///d:/projects/etl_log_collector/checkpoint.py): Coordinates log cursor checks using `ETL_LOG_CHECKPOINT`.
* [config.py](file:///d:/projects/etl_log_collector/config.py): Ingests collector variables from `.env`.

---

### 2. 🔌 Component B: Source Database Monitor (`source_metadata_collector`)
Performs automatic scanning of source tables to evaluate data fresh status.
* [main.py](file:///d:/projects/source_metadata_collector/main.py): Entrypoint to run source tables scanning.
* [collector.py](file:///d:/projects/source_metadata_collector/collector.py): Queries source MySQL schema tables metrics (`Rows`, `Last Updated`, `Columns`) and syncs them to `SOURCE_DB_METADATA`.
* [database.py](file:///d:/projects/source_metadata_collector/database.py): Connector targeting the source MySQL database.
* [config.py](file:///d:/projects/source_metadata_collector/config.py): Configurations file.

---

### 3. ❄️ Component C: Target Database Monitor (`target_metadata_collector`)
Performs automatic scanning of Snowflake schemas to verify ETL loads.
* [main.py](file:///d:/projects/target_metadata_collector/main.py): Entrypoint to run Snowflake targets scanning.
* [collector.py](file:///d:/projects/target_metadata_collector/collector.py): Scans Snowflake database schemas metrics and syncs them to `TARGET_DB_METADATA`.
* [database.py](file:///d:/projects/target_metadata_collector/database.py): Snowflake connector utilizing python's `snowflake.connector` library.
* [config.py](file:///d:/projects/target_metadata_collector/config.py): Snowflake configuration credentials.

---

### ⏰ Component D: Windows Daemon Service (`etl_monitor_service`)
Maintains the background cron worker to coordinate log ingestion and database metadata collectors.
* [windows_service.py](file:///d:/projects/etl_monitor_service/windows_service.py): Wraps the monitor service class as a Windows NT service system agent.
* [main.py](file:///d:/projects/etl_monitor_service/main.py): Entrypoint runner.
* [service.py](file:///d:/projects/etl_monitor_service/service.py): Periodically coordinates calls to `etl_log_collector`, `source_metadata_collector`, and `target_metadata_collector` every `CHECK_INTERVAL` seconds.
* [config.py](file:///d:/projects/etl_monitor_service/config.py): Imports Python and file execution target parameters.

---

### 🖥️ Component E: FastAPI Observability Service Backend (`monitoring_pipelines`)
Serves as the central API manager for metrics, lineage mapping, webhooks, and the AI agent suite.

* [app.py](file:///d:/projects/monitoring_pipelines/app.py): Entry point, mounts CORS, and initializes sub-routers.
* [database.py](file:///d:/projects/monitoring_pipelines/database.py): Pool manager for database connectors.
* [config.py](file:///d:/projects/monitoring_pipelines/config.py): Service configs manager.

#### Sub-Routers, Services & SQL Repositories:
* **AI Agents Console**:
  * [agents_api.py](file:///d:/projects/monitoring_pipelines/agents_api.py): REST paths for AI endpoints.
  * [agents_service.py](file:///d:/projects/monitoring_pipelines/agents_service.py): Interacts with **OpenRouter completions model (`openrouter/auto`)** to identify bugs, compute unified system health rating scores, and predict SLA delivery.
* **Incident Log Console**:
  * [observability_api.py](file:///d:/projects/monitoring_pipelines/observability_api.py): Endpoint to fetch logs.
  * [observability_service.py](file:///d:/projects/monitoring_pipelines/observability_service.py): Chains execution logs with AI troubleshooting steps.
  * [observability_repository.py](file:///d:/projects/monitoring_pipelines/observability_repository.py): DB controller querying execution logs.
* **Pipeline History**:
  * [monitoring_api.py](file:///d:/projects/monitoring_pipelines/monitoring_api.py): Pipeline logs lists.
  * [monitoring_service.py](file:///d:/projects/monitoring_pipelines/monitoring_service.py): Pipeline run counts.
  * [monitoring_repository.py](file:///d:/projects/monitoring_pipelines/monitoring_repository.py): Retrieves execution stats from database logs.
* **Lineage Visualizer**:
  * [lineage_api.py](file:///d:/projects/monitoring_pipelines/lineage_api.py): Generates source table $\rightarrow$ pipeline $\rightarrow$ target Snowflake visual flow maps.
  * [lineage_config.py](file:///d:/projects/monitoring_pipelines/lineage_config.py): Flow charts mapping configs.
* **SLA Freshness**:
  * [freshness_api.py](file:///d:/projects/monitoring_pipelines/freshness_api.py): SLA delay scores.
  * [freshness_service.py](file:///d:/projects/monitoring_pipelines/freshness_service.py): Pinpoints stale tables.
  * [freshness_repository.py](file:///d:/projects/monitoring_pipelines/freshness_repository.py): Fetches target updates compared to source updates.
* **Volume Drifts**:
  * [volume_api.py](file:///d:/projects/monitoring_pipelines/volume_api.py): Target volume status checks.
  * [volume_service.py](file:///d:/projects/monitoring_pipelines/volume_service.py): Flags data loads anomalies.
  * [volume_repository.py](file:///d:/projects/monitoring_pipelines/volume_repository.py): Direct SQL selector evaluating row count stats.
* **Webhooks Registry**:
  * [alerts_api.py](file:///d:/projects/monitoring_pipelines/alerts_api.py): CRUD operations for Slack/MS Teams receivers.
  * [alerts_service.py](file:///d:/projects/monitoring_pipelines/alerts_service.py): Alerts dispatcher logic.
  * [alerts_repository.py](file:///d:/projects/monitoring_pipelines/alerts_repository.py): DB controller reading webhook targets.

---

### 🛠️ Interactive Tooling & Testing
* [test_agents_console.py](file:///d:/projects/test_agents_console.py): Interactive console tool allowing administrators to query AI agents directly in the shell terminal.
