# Azure App Service (Linux) Deployment Notes for Xero AP Automation

## Summary

The Azure startup error:

`ERROR: Could not import module "app.app"`

is caused by a module path mismatch and/or incorrect ZIP packaging structure.

For this project's current layout, the correct startup command is:

`uvicorn app:app --host 0.0.0.0 --port 8000`

Not:

`uvicorn app.app:app --host 0.0.0.0 --port 8000`

## Current Project Layout (Actual)

This repository currently uses a **single module file** at the root:

```text
Xero project 2/
  app.py
  processor.py
  requirements.txt
  xero_secrets.json
  AP_run_template.xlsx
  templates/
    index.html
```

That means Python imports the ASGI app as:

- module: `app`
- object: `app`

So the import target is:

`app:app`

## Why Azure Failed With `app.app:app`

`uvicorn app.app:app` assumes a different layout:

```text
<deployment root>/
  app/
    app.py
```

In that layout:
- outer `app` = Python package/directory
- inner `app` = module file `app.py`

Your current project does **not** have that structure, so Azure cannot import `app.app`.

## Root Cause Analysis (What to Check)

There are four common causes. In your case, the **primary cause** is startup command mismatch.

### 1. Incorrect module path (Primary cause here)

- Current code layout: `app.py` at root
- Azure command used: `uvicorn app.app:app ...`
- Correct command for current layout: `uvicorn app:app ...`

### 2. Nested folder in deployment ZIP (Also common)

If the ZIP contains a parent folder, Azure may extract like:

```text
/tmp/<guid>/AP-xero-take-1/app.py
```

while your startup command expects files at:

```text
/tmp/<guid>/app.py
```

This breaks imports even if the module path is otherwise correct.

### 3. Missing `__init__.py` (Only relevant if using package layout)

If you intentionally deploy:

```text
app/
  app.py
```

then adding `app/__init__.py` is a safe choice (especially for clarity and tooling), but it is **not the issue for the current project**, because you are not using that structure.

### 4. `PYTHONPATH` / Oryx app path confusion

Oryx often runs the app from a generated path like `/tmp/<guid>` and logs:

`App path is set to '/tmp/xxxx'`

That is normal. The key requirement is that your startup command's import target matches the **deployed filesystem layout inside that app path**.

## Cleanest Fix (No App Refactor)

### Recommended (keep current code layout)

Keep the project exactly as-is and set Azure startup command to:

`uvicorn app:app --host 0.0.0.0 --port 8000`

This does not require:
- renaming files
- moving code into a package
- changing business logic

## Correct Deployment ZIP Structure

### Important Rule

ZIP the **contents** of the project folder, not the parent folder itself.

### Correct ZIP (what Azure should receive)

The ZIP root should contain files like:

```text
app.py
processor.py
requirements.txt
xero_secrets.json
AP_run_template.xlsx
templates/index.html
```

### Incorrect ZIP (causes import issues)

If your ZIP root contains a wrapper folder, e.g.:

```text
AP-xero-take-1/
  app.py
  processor.py
  requirements.txt
```

then Azure extracts the wrapper folder too, and startup imports can fail unless your command is adjusted to that nested layout.

## How to Build the ZIP Properly

### Windows PowerShell (from inside the project folder)

Run this from the directory that contains `app.py`:

```powershell
Compress-Archive -Path app.py,processor.py,requirements.txt,xero_secrets.json,AP_run_template.xlsx,templates -DestinationPath deploy.zip -Force
```

This creates a ZIP whose root contains the actual app files.

### If you use File Explorer "Send to ZIP"

Do not ZIP the parent folder itself.

Instead:
1. Open the project folder.
2. Select the files/folders inside it.
3. ZIP the selection.

## Correct Azure Startup Command

For the current project structure:

`uvicorn app:app --host 0.0.0.0 --port 8000`

### When would `uvicorn app.app:app` be correct?

Only if you intentionally deploy this structure:

```text
<root>/
  app/
    __init__.py
    app.py
```

That is not your current layout.

## Azure App Service (Linux / Oryx) Deployment Checklist

1. Confirm `requirements.txt` exists at the ZIP root.
2. Confirm `app.py` exists at the ZIP root.
3. Confirm `templates/index.html` exists.
4. Confirm `xero_secrets.json` is present (temporary approach for now).
5. Set startup command to:
   `uvicorn app:app --host 0.0.0.0 --port 8000`
6. Redeploy ZIP.
7. Restart App Service.
8. Check Log Stream for successful import and startup.

## Where to Put `xero_secrets.json`

For the current implementation (JSON-based secrets), place `xero_secrets.json` in the app root alongside `app.py`.

On Azure after deployment, the deployed app files should include:

```text
/home/site/wwwroot/app.py
/home/site/wwwroot/xero_secrets.json
```

Note: Later, move these values into App Settings / environment variables for production hardening.

## How to Verify in Kudu / SSH

On App Service Linux, use:
- **SSH** from Azure Portal, or
- **Kudu/SCM** tools if enabled (`*.scm.azurewebsites.net`)

### Verify deployed structure

Check that the runtime-visible app path contains your files:

```bash
pwd
ls -la
find . -maxdepth 2 -type f | sort
```

You should see `app.py`, `processor.py`, `requirements.txt`, and `templates/index.html`.

### Verify import manually

```bash
python -c "import app; print(app.__file__)"
python -c "from app import app as asgi_app; print(asgi_app)"
```

If these commands fail, your startup command or ZIP structure is wrong.

## Debugging If It Happens Again

1. Check Azure startup command first.
   - If your file is `app.py` at root -> use `app:app`
   - If your file is `app/app.py` -> use `app.app:app`

2. Inspect ZIP root contents before upload.
   - `app.py` must be at ZIP root for `app:app`

3. Check Azure Log Stream.
   - Look for "App path is set to ..."
   - Then compare expected import path vs actual extracted layout

4. Test imports inside SSH.
   - `python -c "import app"`

5. Confirm Oryx installed dependencies.
   - `pip show fastapi uvicorn`

## Final Recommendation (Current Project)

- Keep the current code layout (no refactor needed).
- Package the project contents at ZIP root.
- Use startup command:
  `uvicorn app:app --host 0.0.0.0 --port 8000`

This is the cleanest fix and preserves local development behavior.
