-- Mercek: datav2 tablolarının Azure SQL şeması (T-SQL).
-- ÜRETİLMİŞ DOSYA: elle değiştirmeyin. Yeniden üretmek için (repo kökünden):
--   python scripts/build_schema.py
-- Kolon tipleri JSON verisinden çıkarılır; boş tablolar datav2/SCHEMA.md'deki tanımla.
-- scripts/load_sql.py tabloları silip yeniden oluşturur; toplu ifadeler GO ile ayrılır.

DROP TABLE IF EXISTS dbo.announcements;
DROP TABLE IF EXISTS dbo.channels;
DROP TABLE IF EXISTS dbo.closure_codes;
DROP TABLE IF EXISTS dbo.customers;
DROP TABLE IF EXISTS dbo.demands;
DROP TABLE IF EXISTS dbo.department_calendar;
DROP TABLE IF EXISTS dbo.departments;
DROP TABLE IF EXISTS dbo.error_handling_rules;
DROP TABLE IF EXISTS dbo.inbound_emails;
DROP TABLE IF EXISTS dbo.incident_categories;
DROP TABLE IF EXISTS dbo.incidents;
DROP TABLE IF EXISTS dbo.institution_screens;
DROP TABLE IF EXISTS dbo.institutions;
DROP TABLE IF EXISTS dbo.kibana_logs;
DROP TABLE IF EXISTS dbo.loans;
DROP TABLE IF EXISTS dbo.org_units;
DROP TABLE IF EXISTS dbo.prevented_calls;
DROP TABLE IF EXISTS dbo.scenarios;
DROP TABLE IF EXISTS dbo.screen_departments;
DROP TABLE IF EXISTS dbo.screens;
DROP TABLE IF EXISTS dbo.solution_templates;
GO

CREATE TABLE dbo.announcements (
    [ann_id] NVARCHAR(50) NOT NULL,
    [source_email_id] NVARCHAR(50) NULL,
    [source] NVARCHAR(20) NULL,
    [institution_code] NVARCHAR(20) NULL,
    [published_at] DATE NULL,
    [effective_at] DATE NULL,
    [title] NVARCHAR(200) NULL,
    [summary] NVARCHAR(500) NULL,
    [screens_json] NVARCHAR(50) NULL,
    [departments_json] NVARCHAR(100) NULL,
    [impact] NVARCHAR(20) NULL,
    [proposed_demand_id] NVARCHAR(50) NULL,
    [status] NVARCHAR(50) NULL,
    [approved_by] NVARCHAR(50) NULL,
    [approved_at] DATETIMEOFFSET(3) NULL,
    CONSTRAINT pk_announcements PRIMARY KEY ([ann_id])
);
GO

CREATE TABLE dbo.channels (
    [channel_id] INT NOT NULL,
    [name] NVARCHAR(100) NULL,
    [incident_channel] NVARCHAR(100) NULL,
    CONSTRAINT pk_channels PRIMARY KEY ([channel_id])
);
GO

CREATE TABLE dbo.closure_codes (
    [code] NVARCHAR(200) NOT NULL,
    [name] NVARCHAR(200) NULL,
    [parent_code] NVARCHAR(200) NULL,
    CONSTRAINT pk_closure_codes PRIMARY KEY ([code])
);
GO

CREATE TABLE dbo.customers (
    [customer_number] NVARCHAR(50) NOT NULL,
    [full_name] NVARCHAR(100) NULL,
    [segment] NVARCHAR(100) NULL,
    [birth_date] DATE NULL,
    [monthly_income] INT NULL,
    [city] NVARCHAR(50) NULL,
    [district] NVARCHAR(50) NULL,
    [email] NVARCHAR(200) NULL,
    [phone] NVARCHAR(100) NULL,
    [perm_email] INT NULL,
    [perm_sms] INT NULL,
    [perm_phone] INT NULL,
    CONSTRAINT pk_customers PRIMARY KEY ([customer_number])
);
GO

CREATE TABLE dbo.demands (
    [demand_id] NVARCHAR(50) NOT NULL,
    [created_at] DATE NULL,
    [demander_unit_id] INT NULL,
    [origin] NVARCHAR(100) NULL,
    [source_announcement_id] NVARCHAR(50) NULL,
    [title] NVARCHAR(500) NULL,
    [description] NVARCHAR(1000) NULL,
    [status] NVARCHAR(50) NULL,
    [type] NVARCHAR(100) NULL,
    [components_json] NVARCHAR(100) NULL,
    [screens_json] NVARCHAR(100) NULL,
    [departments_json] NVARCHAR(1000) NULL,
    [planned_effort_md] INT NULL,
    [actual_effort_md] INT NULL,
    [planned_component_efforts_json] NVARCHAR(100) NULL,
    [actual_component_efforts_json] NVARCHAR(100) NULL,
    [planned_department_efforts_json] NVARCHAR(500) NULL,
    [actual_department_efforts_json] NVARCHAR(500) NULL,
    [decisions] NVARCHAR(500) NULL,
    [analyst] NVARCHAR(50) NULL,
    [approved_by] NVARCHAR(50) NULL,
    [approved_at] DATE NULL,
    [planned_department_id] NVARCHAR(100) NULL,
    [planned_from] DATE NULL,
    [planned_to] DATE NULL,
    [mercek_assigned_analysis_json] NVARCHAR(100) NULL,
    [mercek_suggestions_json] NVARCHAR(100) NULL,
    CONSTRAINT pk_demands PRIMARY KEY ([demand_id])
);
GO

CREATE TABLE dbo.department_calendar (
    [calendar_id] NVARCHAR(50) NOT NULL,
    [department_id] NVARCHAR(100) NULL,
    [demand_id] NVARCHAR(50) NULL,
    [date_from] DATE NULL,
    [date_to] DATE NULL,
    [allocation_pct] INT NULL,
    CONSTRAINT pk_department_calendar PRIMARY KEY ([calendar_id])
);
GO

CREATE TABLE dbo.departments (
    [department_id] NVARCHAR(100) NOT NULL,
    [name] NVARCHAR(200) NULL,
    [description] NVARCHAR(500) NULL,
    CONSTRAINT pk_departments PRIMARY KEY ([department_id])
);
GO

CREATE TABLE dbo.error_handling_rules (
    [rule_id] INT NOT NULL,
    [screen_code] NVARCHAR(50) NULL,
    [error_number] INT NULL,
    [error_code] NVARCHAR(100) NULL,
    [error_type] NVARCHAR(50) NULL,
    [department_id] NVARCHAR(100) NULL,
    [open_incident] INT NULL,
    [explanation_hint] NVARCHAR(500) NULL,
    [source] NVARCHAR(20) NULL,
    [status] NVARCHAR(50) NULL,
    [proposed_at] NVARCHAR(100) NULL,
    [evidence_json] NVARCHAR(100) NULL,
    [approved_by] NVARCHAR(100) NULL,
    [approved_at] NVARCHAR(100) NULL,
    [hit_count] INT NULL,
    CONSTRAINT pk_error_handling_rules PRIMARY KEY ([rule_id])
);
GO

CREATE TABLE dbo.inbound_emails (
    [email_id] NVARCHAR(50) NOT NULL,
    [mailbox] NVARCHAR(200) NULL,
    [received_at] DATETIMEOFFSET(3) NULL,
    [from_address] NVARCHAR(200) NULL,
    [from_display] NVARCHAR(200) NULL,
    [subject] NVARCHAR(500) NULL,
    [body_text] NVARCHAR(2000) NULL,
    [attachments_json] NVARCHAR(200) NULL,
    [assigned_team] NVARCHAR(50) NULL,
    [processing_status] NVARCHAR(50) NULL,
    [processed_by] NVARCHAR(50) NULL,
    [processed_at] DATETIMEOFFSET(3) NULL,
    [mercek_assigned_type] NVARCHAR(100) NULL,
    [mercek_assigned_confidence] NVARCHAR(100) NULL,
    [mercek_assigned_institution_code] NVARCHAR(100) NULL,
    [mercek_assigned_summary] NVARCHAR(100) NULL,
    [linked_announcement_id] NVARCHAR(50) NULL,
    CONSTRAINT pk_inbound_emails PRIMARY KEY ([email_id])
);
GO

CREATE TABLE dbo.incident_categories (
    [category] NVARCHAR(100) NOT NULL,
    [subcategory] NVARCHAR(200) NOT NULL,
    [screen_code] NVARCHAR(50) NULL,
    CONSTRAINT pk_incident_categories PRIMARY KEY ([category], [subcategory])
);
GO

CREATE TABLE dbo.incidents (
    [incident_id] NVARCHAR(50) NOT NULL,
    [created_at] DATETIMEOFFSET(3) NULL,
    [channel] NVARCHAR(100) NULL,
    [reporter_unit_id] INT NULL,
    [reporter_user_name] NVARCHAR(50) NULL,
    [screen_code] NVARCHAR(50) NULL,
    [category] NVARCHAR(100) NULL,
    [subcategory] NVARCHAR(200) NULL,
    [note] NVARCHAR(500) NULL,
    [customer_number] NVARCHAR(50) NULL,
    [kibana_correlation_id] NVARCHAR(200) NULL,
    [department_id] NVARCHAR(100) NULL,
    [mercek_assigned_error_code] NVARCHAR(100) NULL,
    [institution_code] NVARCHAR(20) NULL,
    [master_incident_id] NVARCHAR(100) NULL,
    [priority] INT NULL,
    [status] NVARCHAR(50) NULL,
    [solution_template_id] NVARCHAR(50) NULL,
    [closure_code] NVARCHAR(200) NULL,
    [sub_closure_code] NVARCHAR(100) NULL,
    [resolution_note] NVARCHAR(500) NULL,
    [resolved_at] DATETIMEOFFSET(3) NULL,
    [enriched_json] NVARCHAR(2000) NULL,
    [scenario_path] NVARCHAR(1000) NULL,
    CONSTRAINT pk_incidents PRIMARY KEY ([incident_id])
);
GO

CREATE TABLE dbo.institution_screens (
    [institution_code] NVARCHAR(20) NOT NULL,
    [screen_code] NVARCHAR(50) NULL,
    [usage] NVARCHAR(50) NULL,
    CONSTRAINT pk_institution_screens PRIMARY KEY ([institution_code])
);
GO

CREATE TABLE dbo.institutions (
    [institution_code] NVARCHAR(20) NOT NULL,
    [name] NVARCHAR(100) NULL,
    [bill_type] NVARCHAR(50) NULL,
    [timeout_ms] INT NULL,
    [note] NVARCHAR(200) NULL,
    CONSTRAINT pk_institutions PRIMARY KEY ([institution_code])
);
GO

CREATE TABLE dbo.kibana_logs (
    [log_id] INT NOT NULL,
    [timestamp] DATETIMEOFFSET(3) NULL,
    [log_time] DATETIMEOFFSET(3) NULL,
    [log_level] NVARCHAR(50) NULL,
    [app_name] NVARCHAR(50) NULL,
    [application] NVARCHAR(100) NULL,
    [source_context] NVARCHAR(500) NULL,
    [action_id] INT NULL,
    [action_name] NVARCHAR(100) NULL,
    [request_path] NVARCHAR(200) NULL,
    [referer] NVARCHAR(100) NULL,
    [http_method] NVARCHAR(20) NULL,
    [http_status_code] INT NULL,
    [is_business_exception] BIT NULL,
    [correlation_id] NVARCHAR(200) NULL,
    [message] NVARCHAR(500) NULL,
    [exception_message] NVARCHAR(500) NULL,
    [exception_source] NVARCHAR(200) NULL,
    [exception_stack_trace] NVARCHAR(2000) NULL,
    [inner_exception_message] NVARCHAR(500) NULL,
    [inner_exception_source] NVARCHAR(200) NULL,
    [inner_exception_stack_trace] NVARCHAR(1000) NULL,
    [app_exception_value] INT NULL,
    [message_fields] NVARCHAR(500) NULL,
    [message_filter] NVARCHAR(500) NULL,
    [message_query_string] NVARCHAR(100) NULL,
    [message_response] NVARCHAR(500) NULL,
    [screen_id] NVARCHAR(50) NULL,
    [branch_id] INT NULL,
    [branch_type] NVARCHAR(20) NULL,
    [channel_id] INT NULL,
    [call_id] NVARCHAR(100) NULL,
    [client_id] NVARCHAR(100) NULL,
    [user_name] NVARCHAR(100) NULL,
    [current_date] DATE NULL,
    [customer_id] NVARCHAR(50) NULL,
    [customer_branch_id] INT NULL,
    [session_id] NVARCHAR(200) NULL,
    [session_start_date] DATETIMEOFFSET(3) NULL,
    [event_original] NVARCHAR(4000) NULL,
    [mercek_assigned_error_number] INT NULL,
    CONSTRAINT pk_kibana_logs PRIMARY KEY ([log_id])
);
GO

CREATE TABLE dbo.loans (
    [loan_id] NVARCHAR(50) NOT NULL,
    [customer_number] NVARCHAR(50) NULL,
    [product] NVARCHAR(100) NULL,
    [principal] INT NULL,
    [remaining_principal] FLOAT NULL,
    [monthly_rate] FLOAT NULL,
    [term] INT NULL,
    [installment] FLOAT NULL,
    [paid_installments] INT NULL,
    [next_due_date] DATE NULL,
    [status] NVARCHAR(50) NULL,
    [delinquent_12m] INT NULL,
    CONSTRAINT pk_loans PRIMARY KEY ([loan_id])
);
GO

CREATE TABLE dbo.org_units (
    [unit_id] INT NOT NULL,
    [name] NVARCHAR(200) NULL,
    [unit_type] NVARCHAR(20) NULL,
    [city] NVARCHAR(50) NULL,
    CONSTRAINT pk_org_units PRIMARY KEY ([unit_id])
);
GO

CREATE TABLE dbo.prevented_calls (
    [prevented_id] INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    [ts] DATETIMEOFFSET(3) NULL,
    [user_name] NVARCHAR(50) NULL,
    [screen_code] NVARCHAR(20) NULL,
    [error_code] NVARCHAR(100) NULL,
    [rule_id] NVARCHAR(20) NULL,
    [kibana_correlation_id] NVARCHAR(64) NULL
);
GO

CREATE TABLE dbo.scenarios (
    [scenario_id] NVARCHAR(200) NOT NULL,
    [sort_order] INT NULL,
    [screen_code] NVARCHAR(50) NULL,
    [title] NVARCHAR(200) NULL,
    [description] NVARCHAR(500) NULL,
    [outcome] NVARCHAR(50) NULL,
    [match_screen] NVARCHAR(50) NULL,
    [match_error_number] INT NULL,
    [match_error_code] NVARCHAR(100) NULL,
    [steps] NVARCHAR(MAX) NULL,
    CONSTRAINT pk_scenarios PRIMARY KEY ([scenario_id])
);
GO

CREATE TABLE dbo.screen_departments (
    [screen_code] NVARCHAR(50) NOT NULL,
    [department_id] NVARCHAR(100) NOT NULL,
    [role] NVARCHAR(50) NULL,
    CONSTRAINT pk_screen_departments PRIMARY KEY ([screen_code], [department_id])
);
GO

CREATE TABLE dbo.screens (
    [code] NVARCHAR(50) NOT NULL,
    [name] NVARCHAR(200) NULL,
    [module] NVARCHAR(20) NULL,
    [type] NVARCHAR(20) NULL,
    [description] NVARCHAR(1000) NULL,
    [components_json] NVARCHAR(MAX) NULL,
    [flow_json] NVARCHAR(MAX) NULL,
    [files_json] NVARCHAR(MAX) NULL,
    CONSTRAINT pk_screens PRIMARY KEY ([code])
);
GO

CREATE TABLE dbo.solution_templates (
    [solution_template_id] NVARCHAR(50) NOT NULL,
    [solution_text] NVARCHAR(4000) NULL,
    [closure_code] NVARCHAR(200) NULL,
    [sub_closure_code] NVARCHAR(100) NULL,
    [department_id] NVARCHAR(100) NULL,
    [mercek_assigned_title] NVARCHAR(200) NULL,
    [mercek_assigned_symptom] NVARCHAR(1000) NULL,
    [mercek_assigned_root_cause] NVARCHAR(500) NULL,
    [mercek_assigned_steps] NVARCHAR(2000) NULL,
    [mercek_assigned_error_code] NVARCHAR(100) NULL,
    CONSTRAINT pk_solution_templates PRIMARY KEY ([solution_template_id])
);
GO

CREATE INDEX ix_kibana_logs_screen_time ON dbo.kibana_logs (screen_id, log_time);
GO
