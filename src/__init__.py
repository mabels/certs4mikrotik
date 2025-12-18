"""
certs4devices - Automated certificate deployment from Kubernetes to network devices
"""

__version__ = "1.0.0"

from .cert2device import cli_main, main

__all__ = ['cli_main', 'main']
