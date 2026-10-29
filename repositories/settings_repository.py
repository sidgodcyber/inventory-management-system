"""Data access for the ``settings`` table.

Implements :class:`core.settings_manager.SettingsStore` so the settings manager
can persist values without containing SQL.

Layer: repositories
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from models.setting import Setting
from repositories.base import BaseRepository


class SettingsRepository(BaseRepository):
    """Key/value persistence for runtime settings."""

    SORT_COLUMNS = {"key": "key"}
    DEFAULT_SORT = "key"

    def get_value(self, key: str) -> str | None:
        """Return the raw stored text for ``key`` or ``None``."""
        return self.db.query_value("SELECT value FROM settings WHERE key = ?", (key,))

    def set_value(self, key: str, value: str, value_type: str, description: str) -> None:
        """Insert or update one setting (upsert)."""
        self.db.execute(
            """INSERT INTO settings (key, value, value_type, description, updated_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET
                   value = excluded.value,
                   value_type = excluded.value_type,
                   description = excluded.description,
                   updated_at = excluded.updated_at""",
            (key, value, value_type, description, self.now()),
        )

    def all_values(self) -> dict[str, str]:
        """Return ``{key: raw value}`` for every stored setting."""
        return {row["key"]: row["value"] for row in self.db.query_all("SELECT key, value FROM settings")}

    def list_all(self) -> list[Setting]:
        """Return every stored setting ordered by key."""
        return [Setting.from_row(r) for r in self.db.query_all("SELECT * FROM settings ORDER BY key")]
