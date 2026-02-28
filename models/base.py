# models/base.py
"""
Base model class providing SQLAlchemy declarative base
with ActiveRecord-style helper methods.
"""
from models import Base


class QueryProxy:
    """Chainable query result wrapper"""

    def __init__(self, results=None):
        self._results = results or []

    def first(self):
        return self._results[0] if self._results else None

    def limit(self, n):
        return QueryProxy(self._results[:n])

    def all(self):
        return self._results

    def __iter__(self):
        return iter(self._results)


class Model(Base):
    """Base model with ActiveRecord-style helpers.
    Actual DB operations require an active session from get_db().
    """
    __abstract__ = True

    def save(self):
        """Placeholder — callers must use get_db() sessions directly."""
        pass

    @classmethod
    def create(cls, **kwargs):
        obj = cls(**kwargs)
        obj.save()
        return obj

    @classmethod
    def get_by_id(cls, id):
        return None

    @classmethod
    def where(cls, *args, **kwargs):
        return QueryProxy()

    @classmethod
    def where_in(cls, field, values):
        return QueryProxy()

    @classmethod
    def all(cls, limit=None):
        return QueryProxy()
