"""
Monkey patch to handle missing fastapi-sso dependency gracefully
"""
import sys

# Store original import
_original_import = __builtins__.__import__

def _patched_import(name, *args, **kwargs):
    """Patched import that handles fastapi-sso gracefully"""
    if name == 'fastapi_sso' or name.startswith('fastapi_sso.'):
        # Create a dummy module to prevent ImportError
        class DummyModule:
            def __getattr__(self, name):
                return DummyModule()
            def __call__(self, *args, **kwargs):
                return DummyModule()
        
        module = DummyModule()
        sys.modules[name] = module
        return module
    
    return _original_import(name, *args, **kwargs)

# Apply the patch
__builtins__.__import__ = _patched_import

