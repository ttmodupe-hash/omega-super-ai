"""
OMEGA-LUQI i18n Persistence Layer (UNIFY-14)

One table: i18n_strings — the translation-memory store.
  (key, locale) -> text, with provenance (seed | machine | human).

Serves BOTH the UI string catalogue (seeded keys) and the dynamic
translation memory (machine translations cached by content hash) — one
lookup path, one Postgres store, shared by web/ and cli/ alike.

RLS note: this is SHARED reference data, not user data — country isolation
would break it (every user needs every language). Convention preserved via
FORCE ROW LEVEL SECURITY with an explicit read-for-all policy scoped TO
luqi_app_user; writes flow through the engine owner role only.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Text, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base  # single shared metadata registry


class I18nString(Base):
    __tablename__ = "i18n_strings"

    key: Mapped[str] = mapped_column(String(200), nullable=False)
    locale: Mapped[str] = mapped_column(String(10), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(10), nullable=False, default="seed")  # seed | machine | human
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        PrimaryKeyConstraint("key", "locale", name="pk_i18n_strings"),
    )
