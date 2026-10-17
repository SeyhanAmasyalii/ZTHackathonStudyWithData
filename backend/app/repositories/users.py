"""Demo kullanıcıları (sentetik). user_name, kibana_logs.user_name ile aynıdır.

Bu liste app_users tablosunun tohumudur (scripts/setup_app_tables.py); SQL yoksa doğrudan
kullanılır.
Uygulama kullanıcıları app_store.get_app_store().list_users() ile okur.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DemoUser:
    user_name: str
    name: str
    title: str
    unit: str
    # Etkilenen müşteri listesini (ad, telefon) görebilir mi? Yalnızca L2.
    can_view_customers: bool = False


DEMO_USERS: tuple[DemoUser, ...] = (
    DemoUser("elif", "Elif Demir", "Şube Müşteri Temsilcisi", "601 Kızılay Şubesi"),
    DemoUser("zeynep", "Zeynep Arslan", "Çağrı Merkezi Temsilcisi", "9009 Çağrı Merkezi"),
    DemoUser("kerem", "Kerem Aydın", "L2 Destek", "9010 BT Destek (L2)", can_view_customers=True),
)

# app_users.role ve sıralama (tohum için)
ROLES = {"elif": "sube", "zeynep": "cagri_merkezi", "kerem": "l2"}
