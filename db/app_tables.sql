-- Mercek uygulama tabloları (T-SQL): kullanıcılar, erişim kaydı, konuşma geçmişi.
-- scripts/setup_app_tables.py çalıştırır. Tablolar yoksa oluşturulur, VARSA DOKUNULMAZ (veri silinmez);
-- scripts/load_sql.py bu tabloları silmez. Toplu ifadeler GO ile ayrılır.

IF OBJECT_ID('dbo.app_users') IS NULL
    CREATE TABLE dbo.app_users (
        user_name          NVARCHAR(50)  NOT NULL PRIMARY KEY,
        full_name          NVARCHAR(100) NOT NULL,
        title              NVARCHAR(100) NOT NULL,
        unit               NVARCHAR(100) NOT NULL,
        role               NVARCHAR(20)  NOT NULL,  -- sube / cagri_merkezi / l2
        can_view_customers BIT           NOT NULL DEFAULT 0,
        is_active          BIT           NOT NULL DEFAULT 1,
        sort_order         INT           NOT NULL DEFAULT 0
    );
GO

-- KVKK erişim kaydı: kim, ne zaman, ne yaptı, kaç kayıt. Müşteri bilgisi yazılmaz.
IF OBJECT_ID('dbo.audit_log') IS NULL
    CREATE TABLE dbo.audit_log (
        audit_id   BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        created_at DATETIMEOFFSET(3)    NOT NULL DEFAULT SYSDATETIMEOFFSET(),
        user_name  NVARCHAR(50)         NOT NULL,
        action     NVARCHAR(50)         NOT NULL,
        detail     NVARCHAR(MAX)        NULL,  -- sorgu (JSON)
        row_count  INT                  NULL
    );
GO

IF OBJECT_ID('dbo.conversations') IS NULL
    CREATE TABLE dbo.conversations (
        conversation_id CHAR(32)          NOT NULL PRIMARY KEY,
        user_name       NVARCHAR(50)      NOT NULL,
        created_at      DATETIMEOFFSET(3) NOT NULL DEFAULT SYSDATETIMEOFFSET(),
        updated_at      DATETIMEOFFSET(3) NOT NULL DEFAULT SYSDATETIMEOFFSET()
    );
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_conversations_user')
    CREATE INDEX ix_conversations_user ON dbo.conversations (user_name, updated_at DESC);
GO

IF OBJECT_ID('dbo.conversation_messages') IS NULL
    CREATE TABLE dbo.conversation_messages (
        message_id      BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        conversation_id CHAR(32)             NOT NULL
            REFERENCES dbo.conversations (conversation_id) ON DELETE CASCADE,
        role            NVARCHAR(10)         NOT NULL CHECK (role IN ('user', 'assistant')),
        content         NVARCHAR(MAX)        NOT NULL,
        affected_json   NVARCHAR(MAX)        NULL,  -- L2 "Etkilenen müşteriler" düğmesinin sorgusu
        created_at      DATETIMEOFFSET(3)    NOT NULL DEFAULT SYSDATETIMEOFFSET()
    );
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_conversation_messages_conv')
    CREATE INDEX ix_conversation_messages_conv ON dbo.conversation_messages (conversation_id, message_id);
GO

-- Foundry agent'ının son cevap kimliği (LLM_MODE=agent): model önceki turları Foundry'den hatırlar.
IF COL_LENGTH('dbo.conversations', 'agent_response_id') IS NULL
    ALTER TABLE dbo.conversations ADD agent_response_id NVARCHAR(100) NULL;
GO
