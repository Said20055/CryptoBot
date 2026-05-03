"""
In-memory cache of admin user IDs.

Initialized at startup from .env (permanent) + DB (dynamic).
Env-listed admins cannot be removed via the panel.
"""

_admin_ids: set[int] = set()
_env_admin_ids: frozenset[int] = frozenset()


def init(env_ids: list[int], db_ids: list[int]) -> None:
    global _env_admin_ids
    _env_admin_ids = frozenset(env_ids)
    _admin_ids.update(env_ids)
    _admin_ids.update(db_ids)


def add(user_id: int) -> None:
    _admin_ids.add(user_id)


def remove(user_id: int) -> bool:
    if user_id in _env_admin_ids:
        return False
    _admin_ids.discard(user_id)
    return True


def contains(user_id: int) -> bool:
    return user_id in _admin_ids


def all_ids() -> frozenset[int]:
    return frozenset(_admin_ids)


def is_env_admin(user_id: int) -> bool:
    return user_id in _env_admin_ids
