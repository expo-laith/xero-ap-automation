import os
import shutil
import tempfile
import traceback

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import requests

from processor import run_ap_process, load_secrets, save_secrets

# 🔥 FIX: use the real app directory — NOT os.getcwd()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
AP_TEMPLATE_PATH = os.path.join(BASE_DIR, "AP_run_template.xlsx")

app = FastAPI(debug=True)
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@app.get("/", response_class=HTMLResponse)
async def upload_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/download-template")
async def download_template():
    return FileResponse(
        path=AP_TEMPLATE_PATH,
        filename="AP_run_template.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.get("/authorize-xero")
def authorize_xero():
    """Redirect user to Xero OAuth authorization page."""
    try:
        secrets = load_secrets()
    except FileNotFoundError:
        return HTMLResponse(
            content="<h3>Error: Secrets file not found</h3>"
            "<p>Please ensure /home/xero_secrets.json exists with client_id, client_secret, and redirect_uri.</p>",
            status_code=500
        )
    except Exception as e:
        return HTMLResponse(
            content=f"<h3>Error loading secrets</h3><p>{str(e)}</p>",
            status_code=500
        )
    
    auth_url = (
        "https://login.xero.com/identity/connect/authorize?"
        f"response_type=code"
        f"&client_id={secrets['client_id']}"
        f"&redirect_uri={secrets['redirect_uri']}"
        f"&scope=offline_access accounting.transactions accounting.attachments"
    )
    
    return RedirectResponse(auth_url)


@app.get("/callback")
def xero_callback(code: str):
    """Handle OAuth callback from Xero and exchange code for tokens."""
    try:
        secrets = load_secrets()
    except Exception as e:
        return {"status": "error", "message": f"Failed to load secrets: {str(e)}"}
    
    try:
        token_response = requests.post(
            "https://identity.xero.com/connect/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": secrets["redirect_uri"]
            },
            auth=(secrets["client_id"], secrets["client_secret"]),
            timeout=30
        )
        
        token_response.raise_for_status()
        tokens = token_response.json()
        
        # Update refresh token
        secrets["refresh_token"] = tokens["refresh_token"]
        secrets["access_token"] = tokens.get("access_token", "")
        
        # Get tenant ID
        if tokens.get("access_token"):
            try:
                connections_response = requests.get(
                    "https://api.xero.com/connections",
                    headers={
                        "Authorization": f"Bearer {tokens['access_token']}",
                        "Content-Type": "application/json"
                    },
                    timeout=30
                )
                connections_response.raise_for_status()
                connections = connections_response.json()
                
                if connections:
                    secrets["tenant_id"] = connections[0]["tenantId"]
                    secrets["tenant_name"] = connections[0].get("tenantName", "Unknown")
            except Exception as e:
                print(f"[WARN] Failed to fetch tenant ID: {e}")
        
        save_secrets(secrets)
        
        return HTMLResponse(
            content="<h3>Xero authorized successfully!</h3>"
            "<p>You can close this window and return to the application.</p>"
            "<p><a href='/'>Go back to home</a></p>"
        )
    
    except requests.HTTPError as e:
        return {"status": "error", "message": f"Token exchange failed: {e.response.text}"}
    except Exception as e:
        return {"status": "error", "message": f"Authorization failed: {str(e)}"}


@app.post("/run")
async def run_process(request: Request, file: UploadFile = File(...)):
    suffix = os.path.splitext(file.filename or "")[1] or ".xlsx"
    
    print(f"\n[INFO] Starting /run endpoint - file: {file.filename}")
    
    if suffix.lower() != ".xlsx":
        print(f"[ERROR] Invalid file type: {suffix}")
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "result_message": "Please upload a .xlsx file."},
            status_code=400,
        )

    print("[INFO] Creating temporary file for upload...")
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        temp_path = tmp.name
        shutil.copyfileobj(file.file, tmp)
    print(f"[INFO] Temporary file created: {temp_path}")

    print("[INFO] Creating temporary output directory...")
    run_out_root = tempfile.mkdtemp(prefix="xero_ap_run_")
    print(f"[INFO] Output directory: {run_out_root}")
    
    prev_out_root = os.environ.get("XERO_OUT_ROOT")
    os.environ["XERO_OUT_ROOT"] = run_out_root
    
    print("[INFO] Calling run_ap_process...")
    result = run_ap_process(temp_path)
    print(f"[INFO] Process completed: {result}")
    
    # Restore previous env var
    if prev_out_root is None:
        os.environ.pop("XERO_OUT_ROOT", None)
    else:
        os.environ["XERO_OUT_ROOT"] = prev_out_root

    output_folder = result["output_folder"]
    if not os.path.isabs(output_folder):
        output_folder = os.path.join(BASE_DIR, output_folder)

    print(f"[INFO] Creating ZIP archive from: {output_folder}")
    base_name = os.path.basename(os.path.normpath(output_folder))
    zip_dir = os.path.dirname(os.path.normpath(output_folder))
    zip_base = os.path.join(zip_dir, f"{base_name}_ap_output")
    zip_path = shutil.make_archive(zip_base, "zip", root_dir=output_folder)
    print(f"[INFO] ZIP created: {zip_path}")

    await file.close()
    if temp_path and os.path.exists(temp_path):
        os.remove(temp_path)

    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename=os.path.basename(zip_path),
    )