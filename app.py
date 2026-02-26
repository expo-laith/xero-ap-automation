import os
import shutil
import tempfile
import traceback

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from processor import run_ap_process

# 🔥 FIX: use the real app directory — NOT os.getcwd()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
AP_TEMPLATE_PATH = os.path.join(BASE_DIR, "AP_run_template.xlsx")

app = FastAPI()
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


@app.post("/run")
async def run_process(request: Request, file: UploadFile = File(...)):
    suffix = os.path.splitext(file.filename or "")[1] or ".xlsx"
    temp_path = None
    run_out_root = None

    try:
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
        
        try:
            print("[INFO] Calling run_ap_process...")
            result = run_ap_process(temp_path)
            print(f"[INFO] Process completed: {result}")
        finally:
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

        return FileResponse(
            path=zip_path,
            media_type="application/zip",
            filename=os.path.basename(zip_path),
        )
    except Exception as e:
        print("\n" + "="*80)
        print("ERROR IN /run ENDPOINT")
        print("="*80)
        print(f"Exception type: {type(e).__name__}")
        print(f"Exception message: {str(e)}")
        print("\nFull traceback:")
        traceback.print_exc()
        print("="*80 + "\n")
        
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "result_message": f"Error: {str(e)}"},
            status_code=500,
        )
    finally:
        await file.close()
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)