"""V3 database package — split from legacy db.py."""

from v3.db.connection import ConnectionMixin
from v3.db.schema import SchemaMixin
from v3.db.repositories import RepositoryMixin


class V3Database(ConnectionMixin, SchemaMixin, RepositoryMixin):
    """V3 database manager with SQLite/PostgreSQL backends."""

    pass


__all__ = ["V3Database"]
