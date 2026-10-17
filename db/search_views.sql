-- Mercek: Azure AI Search indexer'ının okuduğu görünüm (T-SQL).
-- scripts/build_search_index.py ve scripts/load_sql.py çalıştırır; tekrar çalıştırmak güvenlidir.
-- Toplu ifadeler GO ile ayrılır.

-- Değişiklik takibi: her satır güncellendiğinde/eklendiğinde artan sayı (veritabanı genelinde).
IF COL_LENGTH('dbo.kibana_logs', 'row_ver') IS NULL
    ALTER TABLE dbo.kibana_logs ADD [row_ver] ROWVERSION;
GO

-- Hata türü = ekran + hata no + hata kodu + kurum (Warning/Error loglar). Her satır AI Search'te bir belge.
-- hwm: türün en yeni logunun row_ver'i; yeni log gelince artar, indexer yalnızca o türü yeniden alır.
CREATE OR ALTER VIEW dbo.v_hata_turleri AS
WITH l AS (
    SELECT
        k.screen_id AS screen_code,
        k.app_exception_value AS error_number,
        JSON_VALUE(k.message_response, '$.errorCode') AS error_code,
        JSON_VALUE(k.message_fields, '$.institutionCode') AS institution_code,
        COALESCE(NULLIF(k.exception_message, ''), k.message) AS msg,
        k.log_time,
        k.customer_id,
        k.row_ver
    FROM dbo.kibana_logs AS k
    WHERE k.log_level IN ('Warning', 'Error')
),
m AS (
    SELECT DISTINCT screen_code, error_number, error_code, institution_code, msg FROM l
),
msgs AS (
    SELECT screen_code, error_number, error_code, institution_code,
           STRING_AGG(msg, ' | ') WITHIN GROUP (ORDER BY msg) AS message
    FROM m
    GROUP BY screen_code, error_number, error_code, institution_code
),
g AS (
    SELECT screen_code, error_number, error_code, institution_code,
           COUNT(*) AS log_count,
           COUNT(DISTINCT customer_id) AS customer_count,
           MIN(log_time) AS first_seen,
           MAX(log_time) AS last_seen,
           CONVERT(BIGINT, MAX(row_ver)) AS hwm
    FROM l
    GROUP BY screen_code, error_number, error_code, institution_code
)
SELECT
    CONCAT_WS('-', g.screen_code, COALESCE(CAST(g.error_number AS NVARCHAR(20)), 'x'),
              COALESCE(g.error_code, 'x'), COALESCE(g.institution_code, 'x')) AS id,
    g.screen_code,
    s.name AS screen_name,
    g.error_number,
    g.error_code,
    g.institution_code,
    i.name AS institution_name,
    i.bill_type,
    msgs.message,
    r.explanation_hint AS explanation,
    REPLACE(CONCAT_WS('. ',
        'Ekran: ' + g.screen_code + COALESCE(' ' + s.name, ''),
        s.description,
        'Kurum: ' + i.name + ' (' + i.bill_type + ')',
        'Hata ' + CONCAT_WS(' ', CAST(g.error_number AS NVARCHAR(20)), g.error_code),
        msgs.message,
        r.explanation_hint
    ), '..', '.') AS content,
    g.log_count,
    g.customer_count,
    g.first_seen,
    g.last_seen,
    g.hwm
FROM g
JOIN msgs
    ON msgs.screen_code = g.screen_code
   AND EXISTS (SELECT msgs.error_number INTERSECT SELECT g.error_number)
   AND EXISTS (SELECT msgs.error_code INTERSECT SELECT g.error_code)
   AND EXISTS (SELECT msgs.institution_code INTERSECT SELECT g.institution_code)
LEFT JOIN dbo.screens AS s ON s.code = g.screen_code
LEFT JOIN dbo.institutions AS i ON i.institution_code = g.institution_code
OUTER APPLY (
    SELECT TOP 1 eh.explanation_hint
    FROM dbo.error_handling_rules AS eh
    WHERE eh.screen_code = g.screen_code AND eh.error_number = g.error_number
    ORDER BY eh.rule_id
) AS r;
GO

-- Hazır çözümler (benzer_cozum_ara, indeks mercek-cozumler): her şablon bir belge.
-- Belgeye o şablonla KAPATILMIŞ çağrıların notları eklenir ("kullanıcıların yazdıkları"): kullanıcı
-- sorunu kendi kelimeleriyle anlattığında eşleşme güçlenir. Müşteri numarası ve kişi bilgisi alınmaz.
IF COL_LENGTH('dbo.solution_templates', 'row_ver') IS NULL
    ALTER TABLE dbo.solution_templates ADD [row_ver] ROWVERSION;
GO

IF COL_LENGTH('dbo.incidents', 'row_ver') IS NULL
    ALTER TABLE dbo.incidents ADD [row_ver] ROWVERSION;
GO

-- hwm: şablonun ya da ona bağlı kapalı çağrılardan birinin en yeni row_ver'i (yeni çağrı kapanınca artar).
CREATE OR ALTER VIEW dbo.v_cozum_sablonlari AS
WITH closed AS (
    SELECT solution_template_id, note, row_ver
    FROM dbo.incidents
    WHERE status = 'kapali' AND solution_template_id IS NOT NULL
),
n AS (
    SELECT DISTINCT solution_template_id, CAST(note AS NVARCHAR(MAX)) AS note
    FROM closed
    WHERE note IS NOT NULL AND note <> ''
),
notes AS (
    SELECT solution_template_id, STRING_AGG(note, ' | ') WITHIN GROUP (ORDER BY note) AS user_notes
    FROM n
    GROUP BY solution_template_id
),
c AS (
    SELECT solution_template_id, COUNT(*) AS closed_count, MAX(row_ver) AS incident_ver
    FROM closed
    GROUP BY solution_template_id
)
SELECT
    t.solution_template_id AS id,
    t.solution_template_id,
    t.mercek_assigned_title AS title,
    t.mercek_assigned_symptom AS symptom,
    t.mercek_assigned_root_cause AS root_cause,
    t.mercek_assigned_steps AS steps,
    t.mercek_assigned_error_code AS error_code,
    t.closure_code,
    t.sub_closure_code,
    t.department_id,
    COALESCE(c.closed_count, 0) AS closed_count,
    notes.user_notes,
    REPLACE(CONCAT_WS('. ',
        t.mercek_assigned_title,
        'Belirti: ' + t.mercek_assigned_symptom,
        'Neden: ' + t.mercek_assigned_root_cause,
        'Hata kodu: ' + t.mercek_assigned_error_code,
        'Kullanıcıların yazdıkları: ' + notes.user_notes
    ), '..', '.') AS content,
    CONVERT(BIGINT, CASE WHEN c.incident_ver > t.row_ver THEN c.incident_ver ELSE t.row_ver END) AS hwm
FROM dbo.solution_templates AS t
LEFT JOIN c ON c.solution_template_id = t.solution_template_id
LEFT JOIN notes ON notes.solution_template_id = t.solution_template_id;
GO
