"""Uygulama tablolarını (kullanıcılar, erişim kaydı, konuşma geçmişi) Azure SQL'de kurar.

Kullanım (repo kökünden):
    uv run --directory backend python ../scripts/setup_app_tables.py

1. db/app_tables.sql: tablolar yoksa oluşturulur; varsa dokunulmaz (geçmiş ve kayıtlar silinmez).
2. app_users, backend/app/repositories/users.py'deki demo kullanıcılarla güncellenir (MERGE).
Tekrar çalıştırmak güvenlidir. Bağlantı backend/.env'den (load_sql.py ile aynı ayarlar).
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

from datav2_tables import schema_batches  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.repositories import sql  # noqa: E402
from app.repositories.users import DEMO_USERS, ROLES  # noqa: E402

MERGE_USERS = """
MERGE dbo.app_users AS t
USING (
    SELECT * FROM OPENJSON(?) WITH (
        user_name NVARCHAR(50) '$.user_name', full_name NVARCHAR(100) '$.full_name',
        title NVARCHAR(100) '$.title', unit NVARCHAR(100) '$.unit', role NVARCHAR(20) '$.role',
        can_view_customers BIT '$.can_view_customers', sort_order INT '$.sort_order'
    )
) AS s
ON t.user_name = s.user_name
WHEN MATCHED THEN UPDATE SET full_name = s.full_name, title = s.title, unit = s.unit,
    role = s.role, can_view_customers = s.can_view_customers, sort_order = s.sort_order,
    is_active = 1
WHEN NOT MATCHED THEN INSERT (user_name, full_name, title, unit, role, can_view_customers,
    sort_order) VALUES (s.user_name, s.full_name, s.title, s.unit, s.role, s.can_view_customers,
    s.sort_order);
"""


def user_rows() -> list[dict]:
    return [
        {
            "user_name": user.user_name,
            "full_name": user.name,
            "title": user.title,
            "unit": user.unit,
            "role": ROLES.get(user.user_name, ""),
            "can_view_customers": user.can_view_customers,
            "sort_order": order,
        }
        for order, user in enumerate(DEMO_USERS, start=1)
    ]


def main() -> None:
    settings = get_settings()
    if not settings.sql_server:
        sys.exit("SQL_SERVER tanımlı değil: backend/.env dosyasına SQL_SERVER=... ekleyin")
    text = (ROOT / "db" / "app_tables.sql").read_text(encoding="utf-8")
    print(f"Bağlanılıyor: {settings.sql_server} / {settings.sql_database}")
    with sql.connect(settings) as connection:
        cursor = connection.cursor()
        for batch in schema_batches(text):
            cursor.execute(batch)
        cursor.execute(MERGE_USERS, [json.dumps(user_rows())])
        connection.commit()
        print("✓ Tablolar hazır: app_users, audit_log, conversations, conversation_messages")
        cursor.execute(
            "SELECT user_name, role, can_view_customers FROM dbo.app_users ORDER BY sort_order"
        )
        for user_name, role, can_view in cursor.fetchall():
            print(f"  {user_name:<8} {role:<14} müşteri listesi: {'evet' if can_view else 'hayır'}")
        for table in ("audit_log", "conversations", "conversation_messages"):
            cursor.execute(f"SELECT COUNT(*) FROM dbo.{table}")
            print(f"✓ {table}: {cursor.fetchone()[0]} kayıt")


if __name__ == "__main__":
    main()
