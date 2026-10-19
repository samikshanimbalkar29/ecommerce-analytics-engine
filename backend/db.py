
"""Cassandra data-access layer for the dashboard.

Uses the asyncio connection implementation for Python 3.12+
to avoid the removed asyncore module.

Aggregations are performed by the API layer.
"""

import sys
import config

QUERIES = {
    "summary": (
        "SELECT amount FROM orders WHERE region = ?"
    ),
    "category": (
        "SELECT category, amount "
        "FROM orders_by_category WHERE region = ?"
    ),
    "daily": (
        "SELECT order_date, amount "
        "FROM orders WHERE region = ?"
    ),
}


class _CqlFuture:
    """Wrapper around the Cassandra asynchronous response."""

    def __init__(self, response_future):
        self._future = response_future

    def result(self):
        """Return the query results as tuples."""
        rows = self._future.result()
        return [tuple(row) for row in rows]


class CassandraBackend:
    """Cassandra-backed dashboard data-access layer."""

    name = "Apache Cassandra"

    def __init__(self):
        from cassandra.cluster import (
            Cluster,
            ExecutionProfile,
            EXEC_PROFILE_DEFAULT,
        )

        connection_options = {}

        if sys.version_info >= (3, 12):
            from cassandra.io.asyncioreactor import (
                AsyncioConnection,
            )

            connection_options["connection_class"] = (
                AsyncioConnection
            )

        profile = ExecutionProfile(
            request_timeout=config.REQUEST_TIMEOUT
        )

        self.cluster = Cluster(
            contact_points=config.HOSTS,
            port=config.PORT,
            execution_profiles={
                EXEC_PROFILE_DEFAULT: profile,
            },
            **connection_options,
        )

        try:
            self.session = self.cluster.connect(
                config.KEYSPACE
            )

            self.stmts = {
                name: self.session.prepare(cql)
                for name, cql in QUERIES.items()
            }

        except Exception:
            self.cluster.shutdown()
            raise

    def submit(self, query, region):
        """Submit a prepared query asynchronously."""
        if query not in self.stmts:
            raise ValueError(
                f"Unknown query: {query!r}"
            )

        future = self.session.execute_async(
            self.stmts[query],
            [region],
        )

        return _CqlFuture(future)

    def close(self):
        """Shut down the Cassandra connection."""
        self.cluster.shutdown()


def make_backend():
    """Create the Cassandra backend without mock-data fallback."""
    return CassandraBackend()
