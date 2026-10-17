-- Mercek M1: sohbetin okuduğu datav2 tabloları (Azure SQL / T-SQL).
-- scripts/load_sql.py bu dosyayı çalıştırır: tablolar silinip yeniden oluşturulur, sonra JSON'dan doldurulur.
-- Kolonlar datav2/SCHEMA.md'deki adlarla aynıdır; yalnızca backend'in kullandığı alt küme.
-- Toplu ifadeler "GO" satırıyla ayrılır.

DROP TABLE IF EXISTS dbo.incidents;
DROP TABLE IF EXISTS dbo.solution_templates;
DROP TABLE IF EXISTS dbo.institution_screens;
DROP TABLE IF EXISTS dbo.institutions;
DROP TABLE IF EXISTS dbo.screens;
DROP TABLE IF EXISTS dbo.kibana_logs;
GO

CREATE TABLE dbo.screens (
    code        NVARCHAR(20)   NOT NULL PRIMARY KEY,
    name        NVARCHAR(200)  NOT NULL,
    description NVARCHAR(MAX)  NULL
);
GO

CREATE TABLE dbo.institutions (
    institution_code NVARCHAR(20)  NOT NULL PRIMARY KEY,
    name             NVARCHAR(200) NOT NULL,
    bill_type        NVARCHAR(50)  NULL
);
GO

CREATE TABLE dbo.institution_screens (
    institution_code NVARCHAR(20) NOT NULL,
    screen_code      NVARCHAR(20) NOT NULL,
    CONSTRAINT pk_institution_screens PRIMARY KEY (institution_code, screen_code)
);
GO

CREATE TABLE dbo.solution_templates (
    solution_template_id  NVARCHAR(20)  NOT NULL PRIMARY KEY,
    solution_text         NVARCHAR(MAX) NULL,
    mercek_assigned_title NVARCHAR(300) NULL
);
GO

CREATE TABLE dbo.incidents (
    incident_id                NVARCHAR(20)      NOT NULL PRIMARY KEY,
    created_at                 DATETIMEOFFSET(3) NOT NULL,
    status                     NVARCHAR(20)      NOT NULL,
    screen_code                NVARCHAR(20)      NULL,
    institution_code           NVARCHAR(20)      NULL,
    kibana_correlation_id      NVARCHAR(64)      NULL,
    mercek_assigned_error_code NVARCHAR(100)     NULL,
    note                       NVARCHAR(MAX)     NULL,
    resolution_note            NVARCHAR(MAX)     NULL,
    closure_code               NVARCHAR(50)      NULL,
    sub_closure_code           NVARCHAR(50)      NULL,
    solution_template_id       NVARCHAR(20)      NULL,
    reporter_user_name         NVARCHAR(50)      NULL,
    scenario_path              NVARCHAR(400)     NULL
);
GO

CREATE TABLE dbo.kibana_logs (
    log_id              BIGINT            NOT NULL PRIMARY KEY,
    log_time            DATETIMEOFFSET(3) NOT NULL,
    log_level           NVARCHAR(20)      NOT NULL,
    user_name           NVARCHAR(50)      NULL,
    customer_id         NVARCHAR(20)      NULL,
    screen_id           NVARCHAR(20)      NULL,
    app_exception_value INT               NULL,
    correlation_id      NVARCHAR(64)      NULL,
    message             NVARCHAR(MAX)     NULL,
    exception_message   NVARCHAR(MAX)     NULL,
    message_fields      NVARCHAR(MAX)     NULL,
    message_response    NVARCHAR(MAX)     NULL
);
GO

CREATE INDEX ix_kibana_logs_screen_time ON dbo.kibana_logs (screen_id, log_time);
GO
