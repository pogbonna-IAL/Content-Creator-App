# Uvicorn Startup Error Fix

**Error:** `ModuleNotFoundError: No module named 'app'`

**Cause:** Uvicorn is being called with the wrong module name.

---

## Problem

When running uvicorn directly, you must specify the correct module name. The error occurs when uvicorn tries to import a module called `app`, but the actual module is `api_server`.

## Solutions

### ✅ Solution 1: Use the Python script directly (Recommended)

Instead of calling uvicorn directly, run the Python script:

```bash
python api_server.py
```

This is the recommended approach because:
- The script handles all uvicorn configuration
- It sets up logging correctly
- It configures the FastAPI app properly

### ✅ Solution 2: Use uvicorn with correct module name

If you need to use uvicorn directly, use the correct module name:

```bash
uvicorn api_server:app --host 0.0.0.0 --port 8000
```

**Important:** Use `api_server:app`, not `app:app`

### ✅ Solution 3: Use the start script

Use the provided startup script:

```bash
# On Linux/Mac
./start_backend.sh

# On Windows (PowerShell)
.\start_backend.sh
```

Or with uv:

```bash
uv run python api_server.py
```

---

## Docker/Container Usage

### Dockerfile (Main)
The main `Dockerfile` uses:
```dockerfile
CMD ["python", "api_server.py"]
```
✅ This is correct and should work.

### Dockerfile.api (Alternative)
The alternative `Dockerfile.api` uses:
```dockerfile
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
```
✅ This is also correct, but requires the module to be importable.

---

## Railway Deployment

The `railway.json` specifies:
```json
{
  "deploy": {
    "startCommand": "python api_server.py"
  }
}
```
✅ This is correct and should work.

---

## Common Mistakes

### ❌ Wrong:
```bash
uvicorn app:app  # Module 'app' doesn't exist
```

### ✅ Correct:
```bash
python api_server.py  # Recommended
# OR
uvicorn api_server:app  # If you must use uvicorn directly
```

---

## Verification

To verify the correct module name, check `api_server.py`:

```python
# In api_server.py, you'll find:
app = FastAPI(...)  # The FastAPI instance is named 'app'
```

So the module is `api_server` and the FastAPI instance is `app`, hence: `api_server:app`

---

## Troubleshooting

If you're still getting the error:

1. **Check your current directory:**
   ```bash
   pwd  # Should be in project root
   ls api_server.py  # Should exist
   ```

2. **Check Python path:**
   ```bash
   python -c "import api_server; print('✓ Module found')"
   ```

3. **Check if api_server.py exists:**
   ```bash
   ls -la api_server.py
   ```

4. **Use the Python script directly:**
   ```bash
   python api_server.py
   ```

---

**Status:** ✅ Fixed - Use `python api_server.py` or `uvicorn api_server:app`
