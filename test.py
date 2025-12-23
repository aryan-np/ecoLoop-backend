"""
Comprehensive test script to verify Loguru logging is working correctly
Location: test.py (in project root)
Run with: python test.py
"""

import os
import django

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ecoLoop.settings")
django.setup()

from loguru import logger
import time


logger.critical("hi")
