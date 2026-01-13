#!/usr/bin/env python
"""
Export OpenAPI schema to JSON file
"""
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from api_server import app
    
    # Generate OpenAPI schema
    openapi_schema = app.openapi()
    
    # Write to docs/openapi.json
    output_path = project_root / "docs" / "openapi.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
    
    print(f"✓ OpenAPI schema exported to {output_path}")
    print(f"  Schema version: {openapi_schema.get('openapi', 'unknown')}")
    print(f"  API title: {openapi_schema.get('info', {}).get('title', 'unknown')}")
    print(f"  API version: {openapi_schema.get('info', {}).get('version', 'unknown')}")
    print(f"  Endpoints: {len(openapi_schema.get('paths', {}))}")
    
except Exception as e:
    print(f"✗ Error exporting OpenAPI schema: {e}", file=sys.stderr)
    sys.exit(1)

