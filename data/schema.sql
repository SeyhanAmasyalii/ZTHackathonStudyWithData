-- Mercek veritabanı şeması (Azure SQL / T-SQL). tools/mercek_data/db.py tablo tanımlarından üretilir;
-- elle düzenlemeyin: python3 tools/mercek_data/load_all.py --write-schema

DROP TABLE IF EXISTS mercek_events;

DROP TABLE IF EXISTS requests;

DROP TABLE IF EXISTS incidents;

DROP TABLE IF EXISTS solutions;

DROP TABLE IF EXISTS contacts;

DROP TABLE IF EXISTS banking_logs;

DROP TABLE IF EXISTS loans;

DROP TABLE IF EXISTS customers;

DROP TABLE IF EXISTS announcements;

DROP TABLE IF EXISTS scope_addons;

DROP TABLE IF EXISTS service_calendar;

DROP TABLE IF EXISTS error_rules;

DROP TABLE IF EXISTS screen_services;

DROP TABLE IF EXISTS screens;

DROP TABLE IF EXISTS services;

CREATE TABLE services (
  service_id NVARCHAR(40) NOT NULL,
  name NVARCHAR(120) NOT NULL,
  description NVARCHAR(MAX),
  PRIMARY KEY (service_id)
);

CREATE TABLE screens (
  code NVARCHAR(8) NOT NULL,
  name NVARCHAR(120) NOT NULL,
  module NVARCHAR(3) NOT NULL,
  type NVARCHAR(1) NOT NULL,
  simulated BIT NOT NULL,
  description NVARCHAR(MAX),
  components_json NVARCHAR(MAX) CHECK (components_json IS NULL OR ISJSON(components_json) = 1),
  flow_json NVARCHAR(MAX) CHECK (flow_json IS NULL OR ISJSON(flow_json) = 1),
  files_json NVARCHAR(MAX) CHECK (files_json IS NULL OR ISJSON(files_json) = 1),
  PRIMARY KEY (code)
);

CREATE TABLE screen_services (
  screen_code NVARCHAR(8) NOT NULL,
  service_id NVARCHAR(40) NOT NULL,
  role NVARCHAR(20) NOT NULL,
  PRIMARY KEY (screen_code, service_id)
);

CREATE TABLE error_rules (
  screen_code NVARCHAR(8) NOT NULL,
  error_code NVARCHAR(40) NOT NULL,
  error_type NVARCHAR(20) NOT NULL,
  service_id NVARCHAR(40),
  open_incident BIT NOT NULL,
  explanation_hint NVARCHAR(MAX),
  PRIMARY KEY (screen_code, error_code)
);

CREATE TABLE service_calendar (
  service_id NVARCHAR(40) NOT NULL,
  date_from DATE NOT NULL,
  date_to DATE NOT NULL,
  allocation_pct INT NOT NULL,
  note NVARCHAR(200),
  PRIMARY KEY (service_id, date_from)
);

CREATE TABLE scope_addons (
  addon_id NVARCHAR(40) NOT NULL,
  name NVARCHAR(200) NOT NULL,
  effort_md INT NOT NULL,
  main_share INT NOT NULL,
  customer_mgmt_share INT NOT NULL,
  PRIMARY KEY (addon_id)
);

CREATE TABLE announcements (
  ann_id NVARCHAR(20) NOT NULL,
  institution NVARCHAR(80) NOT NULL,
  published_at DATE NOT NULL,
  effective_at DATE NOT NULL,
  title NVARCHAR(300) NOT NULL,
  body NVARCHAR(MAX) NOT NULL,
  search_text AS (CONCAT_WS(NCHAR(10), institution, title, body)) PERSISTED,
  PRIMARY KEY (ann_id)
);

CREATE TABLE customers (
  customer_number NVARCHAR(12) NOT NULL,
  full_name NVARCHAR(120) NOT NULL,
  segment NVARCHAR(40) NOT NULL,
  age INT,
  monthly_income INT,
  city NVARCHAR(40) NOT NULL,
  district NVARCHAR(40),
  region_affected BIT NOT NULL,
  address_changed_at DATE,
  email NVARCHAR(120),
  phone NVARCHAR(30),
  perm_email BIT NOT NULL,
  perm_sms BIT NOT NULL,
  perm_phone BIT NOT NULL,
  in_logs BIT NOT NULL,
  PRIMARY KEY (customer_number)
);

CREATE TABLE loans (
  loan_id NVARCHAR(12) NOT NULL,
  customer_number NVARCHAR(12) NOT NULL,
  product NVARCHAR(60) NOT NULL,
  principal FLOAT NOT NULL,
  remaining_principal FLOAT NOT NULL,
  monthly_rate FLOAT NOT NULL,
  term INT NOT NULL,
  installment FLOAT NOT NULL,
  paid_installments INT NOT NULL,
  next_due_date DATE NOT NULL,
  status NVARCHAR(20) NOT NULL,
  delinquent_12m BIT NOT NULL,
  collection_account NVARCHAR(34),
  PRIMARY KEY (loan_id)
);

CREATE TABLE banking_logs (
  log_id BIGINT IDENTITY(1,1) NOT NULL,
  ts DATETIMEOFFSET(3) NOT NULL,
  level NVARCHAR(10) NOT NULL,
  screen_code NVARCHAR(8) NOT NULL,
  event_action NVARCHAR(40),
  outcome NVARCHAR(20),
  error_code NVARCHAR(40),
  error_type NVARCHAR(20),
  error_field NVARCHAR(40),
  customer_number NVARCHAR(12),
  trace_id NVARCHAR(40),
  channel NVARCHAR(30),
  branch_code NVARCHAR(10),
  employee_id NVARCHAR(20),
  institution NVARCHAR(80),
  subscriber_no NVARCHAR(30),
  subscriber_no_len INT,
  amount FLOAT,
  message NVARCHAR(1000),
  source NVARCHAR(10),
  raw_json NVARCHAR(MAX) CHECK (raw_json IS NULL OR ISJSON(raw_json) = 1),
  PRIMARY KEY (log_id)
);

CREATE TABLE contacts (
  contact_id NVARCHAR(12) NOT NULL,
  created_at DATETIMEOFFSET(3) NOT NULL,
  channel NVARCHAR(20) NOT NULL,
  customer_number NVARCHAR(12),
  city NVARCHAR(40),
  region_affected BIT NOT NULL,
  category NVARCHAR(60) NOT NULL,
  subcategory NVARCHAR(80) NOT NULL,
  note NVARCHAR(MAX),
  incident_id NVARCHAR(16),
  PRIMARY KEY (contact_id)
);

CREATE TABLE solutions (
  solution_id NVARCHAR(10) NOT NULL,
  title NVARCHAR(300) NOT NULL,
  symptom NVARCHAR(MAX),
  root_cause NVARCHAR(MAX),
  steps NVARCHAR(MAX) CHECK (steps IS NULL OR ISJSON(steps) = 1),
  error_code NVARCHAR(40),
  service_id NVARCHAR(40),
  search_text AS (CONCAT_WS(NCHAR(10), title, symptom, root_cause, steps)) PERSISTED,
  PRIMARY KEY (solution_id)
);

CREATE TABLE incidents (
  incident_id NVARCHAR(16) NOT NULL,
  created_at DATETIMEOFFSET(3) NOT NULL,
  channel NVARCHAR(20) NOT NULL,
  screen_code NVARCHAR(8),
  category NVARCHAR(60),
  subcategory NVARCHAR(80),
  note NVARCHAR(MAX),
  customer_number NVARCHAR(12),
  subscriber_no NVARCHAR(30),
  trace_id NVARCHAR(40),
  city NVARCHAR(40),
  service_id NVARCHAR(40),
  error_code NVARCHAR(40),
  institution NVARCHAR(80),
  master_incident_id NVARCHAR(16),
  status NVARCHAR(10) NOT NULL,
  solution_id NVARCHAR(10),
  resolution_minutes INT,
  enriched_json NVARCHAR(MAX) CHECK (enriched_json IS NULL OR ISJSON(enriched_json) = 1),
  PRIMARY KEY (incident_id)
);

CREATE TABLE requests (
  request_id NVARCHAR(10) NOT NULL,
  created_at DATE NOT NULL,
  requester_unit NVARCHAR(80),
  title NVARCHAR(300) NOT NULL,
  description NVARCHAR(MAX),
  type NVARCHAR(20) NOT NULL,
  components_json NVARCHAR(MAX) CHECK (components_json IS NULL OR ISJSON(components_json) = 1),
  screens_json NVARCHAR(MAX) CHECK (screens_json IS NULL OR ISJSON(screens_json) = 1),
  services_json NVARCHAR(MAX) CHECK (services_json IS NULL OR ISJSON(services_json) = 1),
  effort_md INT,
  component_efforts_json NVARCHAR(MAX) CHECK (component_efforts_json IS NULL OR ISJSON(component_efforts_json) = 1),
  service_efforts_json NVARCHAR(MAX) CHECK (service_efforts_json IS NULL OR ISJSON(service_efforts_json) = 1),
  decisions NVARCHAR(MAX),
  analysis_json NVARCHAR(MAX) CHECK (analysis_json IS NULL OR ISJSON(analysis_json) = 1),
  analyst NVARCHAR(80),
  approved_by NVARCHAR(80),
  scope_additions NVARCHAR(MAX) CHECK (scope_additions IS NULL OR ISJSON(scope_additions) = 1),
  status NVARCHAR(20) NOT NULL,
  planned_service_id NVARCHAR(40),
  planned_from DATE,
  planned_to DATE,
  search_text AS (CONCAT_WS(NCHAR(10), title, description)) PERSISTED,
  PRIMARY KEY (request_id)
);

CREATE TABLE mercek_events (
  event_id BIGINT IDENTITY(1,1) NOT NULL,
  ts DATETIMEOFFSET(3) NOT NULL,
  kind NVARCHAR(30) NOT NULL,
  screen_code NVARCHAR(8),
  incident_id NVARCHAR(16),
  duration_ms INT,
  tokens INT,
  detail_json NVARCHAR(MAX) CHECK (detail_json IS NULL OR ISJSON(detail_json) = 1),
  PRIMARY KEY (event_id)
);

CREATE INDEX ix_banking_logs_1 ON banking_logs (screen_code, ts);

CREATE INDEX ix_banking_logs_2 ON banking_logs (institution, ts);

CREATE INDEX ix_banking_logs_3 ON banking_logs (trace_id);

CREATE INDEX ix_banking_logs_4 ON banking_logs (customer_number, ts);

CREATE INDEX ix_banking_logs_5 ON banking_logs (error_code, error_field, ts);

CREATE INDEX ix_contacts_6 ON contacts (category, subcategory, created_at);

CREATE INDEX ix_contacts_7 ON contacts (region_affected, created_at);

CREATE INDEX ix_incidents_8 ON incidents (screen_code, institution, error_code, status);

CREATE INDEX ix_incidents_9 ON incidents (master_incident_id);

CREATE INDEX ix_loans_10 ON loans (customer_number);

CREATE INDEX ix_customers_11 ON customers (region_affected);

CREATE INDEX ix_banking_logs_12 ON banking_logs (source);


-- AI Search indexer için değişiklik takibi (transaction dışında; load_all.py --sql kendisi çalıştırır)
IF NOT EXISTS (SELECT 1 FROM sys.change_tracking_databases WHERE database_id = DB_ID()) ALTER DATABASE CURRENT SET CHANGE_TRACKING = ON (CHANGE_RETENTION = 2 DAYS, AUTO_CLEANUP = ON);
ALTER TABLE solutions ENABLE CHANGE_TRACKING;
ALTER TABLE requests ENABLE CHANGE_TRACKING;
ALTER TABLE announcements ENABLE CHANGE_TRACKING;
