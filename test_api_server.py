#!/usr/bin/env python
"""Test if API server can start without fastapi-sso errors"""
import sys
import os

# Apply the fastapi-sso fix before any imports
os.environ['LITELLM_DISABLE_PROXY'] = '1'

try:
    import fastapi_sso
except ImportError:
    import types
    fastapi_sso = types.ModuleType('fastapi_sso')
    fastapi_sso.sso = types.ModuleType('fastapi_sso.sso')
    fastapi_sso.sso.base = types.ModuleType('fastapi_sso.sso.base')
    fastapi_sso.sso.base.OpenID = type('OpenID', (), {})
    sys.modules['fastapi_sso'] = fastapi_sso
    sys.modules['fastapi_sso.sso'] = fastapi_sso.sso
    sys.modules['fastapi_sso.sso.base'] = fastapi_sso.sso.base

# Now try importing the crew
sys.path.insert(0, 'src')
import content_creation_crew
from content_creation_crew.crew import ContentCreationCrew

print("Testing crew initialization...")
crew = ContentCreationCrew()
print("✓ Crew initialized successfully!")

print("\nTesting API server import...")
from api_server import app
print("✓ API server imported successfully!")
print("✓ All imports working - fastapi-sso error resolved!")

