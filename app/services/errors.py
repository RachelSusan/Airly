"""Service-layer exceptions."""


class UpstreamError(Exception):
    """An external data provider failed or returned unusable data."""
