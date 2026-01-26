# Windows signal compatibility patch - MUST run before any crewai imports
# This runs when the package is first imported, ensuring signals are patched
# before any crewai modules try to access them
import sys
import os

# Prevent LiteLLM from importing proxy modules we don't need (avoids fastapi-sso dependency)
os.environ['LITELLM_DISABLE_PROXY'] = '1'
# Set LiteLLM timeout to 30 minutes (1800 seconds) for long-running content generation
# These must be set before importing/using LiteLLM
os.environ['LITELLM_REQUEST_TIMEOUT'] = '1800'
os.environ['LITELLM_TIMEOUT'] = '1800'
os.environ['LITELLM_CONNECTION_TIMEOUT'] = '1800'

# Disable CrewAI tracing to prevent interactive prompts (critical for serverless/containerized environments)
os.environ['CREWAI_TRACING_ENABLED'] = 'false'
os.environ['CREWAI_TRACING'] = 'false'

# Also configure litellm directly if available
try:
    import litellm
    litellm.request_timeout = 1800
    litellm.timeout = 1800
    litellm.drop_params = True  # Don't drop timeout params
    
    # Configure httpx timeout for Ollama connections
    # httpx has a default timeout of 600 seconds, we need to override it
    try:
        import httpx
        # Patch httpx.Client to use extended timeout by default
        # LiteLLM creates httpx clients internally, so we need to patch the Client class
        _original_client_init = httpx.Client.__init__
        def _patched_client_init(self, *args, timeout=None, **kwargs):
            # If timeout is not provided or is <= 600 seconds (httpx default), use 1800 seconds
            if timeout is None:
                timeout = httpx.Timeout(1800.0, connect=60.0)
            elif isinstance(timeout, (int, float)):
                if timeout <= 600:
                    # Extend timeout to 1800 seconds
                    timeout = httpx.Timeout(1800.0, connect=60.0)
                else:
                    # Use provided timeout but ensure connect timeout is reasonable
                    timeout = httpx.Timeout(timeout, connect=60.0)
            elif isinstance(timeout, httpx.Timeout):
                # If it's already a Timeout object, check if read timeout is <= 600
                read_timeout = getattr(timeout, 'read', None) or getattr(timeout, 'timeout', None)
                if read_timeout is None or read_timeout <= 600:
                    # Extend timeout to 1800 seconds
                    timeout = httpx.Timeout(1800.0, connect=60.0)
            return _original_client_init(self, *args, timeout=timeout, **kwargs)
        httpx.Client.__init__ = _patched_client_init
        
        # Also patch AsyncClient for async operations
        _original_async_client_init = httpx.AsyncClient.__init__
        def _patched_async_client_init(self, *args, timeout=None, **kwargs):
            if timeout is None:
                timeout = httpx.Timeout(1800.0, connect=60.0)
            elif isinstance(timeout, (int, float)):
                if timeout <= 600:
                    timeout = httpx.Timeout(1800.0, connect=60.0)
                else:
                    timeout = httpx.Timeout(timeout, connect=60.0)
            elif isinstance(timeout, httpx.Timeout):
                read_timeout = getattr(timeout, 'read', None) or getattr(timeout, 'timeout', None)
                if read_timeout is None or read_timeout <= 600:
                    timeout = httpx.Timeout(1800.0, connect=60.0)
            return _original_async_client_init(self, *args, timeout=timeout, **kwargs)
        httpx.AsyncClient.__init__ = _patched_async_client_init
    except (ImportError, AttributeError):
        pass
except ImportError:
    pass

if sys.platform == 'win32':
    import signal
    # Patch signals immediately, before any other imports
    unix_signals = {
        'SIGHUP': 1,
        'SIGTSTP': 20,
        'SIGCONT': 18,
        'SIGQUIT': 3,
        'SIGUSR1': 10,
        'SIGUSR2': 12,
    }
    for sig_name, sig_value in unix_signals.items():
        if not hasattr(signal, sig_name):
            setattr(signal, sig_name, sig_value)

