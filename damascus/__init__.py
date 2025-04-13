"""
Damascus - Secure integration SDK for ReadonlyREST ecosystem.

A powerful Python SDK for creating secure and efficient integrations
with the ReadonlyREST ecosystem.

Runtime compatibility: Python 3.8+
Development requirements: Python 3.13+ with uv
"""

__version__ = "0.1.0"
__author__ = "Beshu Limited"
__email__ = "info@beshu.tech"
__license__ = "GPLv3"

from damascus.client import Client
from damascus.exceptions import DamascusError, AuthenticationError, ConfigurationError

__all__ = ["Client", "DamascusError", "AuthenticationError", "ConfigurationError"]
