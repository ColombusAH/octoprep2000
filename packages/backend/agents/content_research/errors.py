"""Research provider errors — caught by fetcher; never fail report generation."""


class ResearchProviderError(Exception):
    """A single external research call failed."""
