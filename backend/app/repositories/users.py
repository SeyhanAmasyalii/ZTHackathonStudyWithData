"""Demo kullanıcıları (sentetik). user_name, kibana_logs.user_name ile aynıdır."""

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

_BY_NAME = {user.user_name: user for user in DEMO_USERS}


def find_user(user_name: str) -> DemoUser | None:
    return _BY_NAME.get(user_name)
