#!/usr/bin/env python
"""Generate a Fernet master key for API key encryption."""
from cryptography.fernet import Fernet
import sys

key = Fernet.generate_key().decode()
print(f"MASTER_KEY={key}")
print("\nAdd to .env:")
print(f"MASTER_KEY={key}")
print("\nIMPORTANT: Store this securely. Losing it = losing all stored API keys.")