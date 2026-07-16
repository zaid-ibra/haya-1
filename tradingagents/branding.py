"""Central branding constants for the HAYA-ZAID distribution."""

PROJECT_NAME = "HAYA-ZAID"
FULL_NAME = "HAYA-ZAID AI Trading System"
TAGLINE = "Professional Gold Trading Platform"
VERSION = "1.0.0"
MT5_COMMENT = "HAYA-ZAID AI"


def banner() -> str:
    return f"""
============================================================
{FULL_NAME}
{TAGLINE}
Version {VERSION}
============================================================
""".strip()
