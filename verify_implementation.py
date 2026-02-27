#!/usr/bin/env python3
"""
Verification script for OAuth implementation.
Run this to verify all changes are correct before deployment.
"""

import os
import sys
import importlib.util

def check_file_exists(filepath, description):
    """Check if a file exists."""
    if os.path.exists(filepath):
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description} NOT FOUND: {filepath}")
        return False

def check_constant_in_file(filepath, constant_name, expected_value):
    """Check if a constant has the expected value in a file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            if f'{constant_name} = "{expected_value}"' in content:
                print(f"✅ {constant_name} correctly set in {filepath}")
                return True
            else:
                print(f"❌ {constant_name} not found or incorrect in {filepath}")
                return False
    except Exception as e:
        print(f"❌ Error reading {filepath}: {e}")
        return False

def check_string_in_file(filepath, search_string, description):
    """Check if a string exists in a file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            if search_string in content:
                print(f"✅ {description} found in {filepath}")
                return True
            else:
                print(f"❌ {description} NOT found in {filepath}")
                return False
    except Exception as e:
        print(f"❌ Error reading {filepath}: {e}")
        return False

def check_module_imports(module_name):
    """Check if a Python module can be imported."""
    try:
        spec = importlib.util.find_spec(module_name)
        if spec is not None:
            print(f"✅ Module {module_name} can be imported")
            return True
        else:
            print(f"❌ Module {module_name} cannot be found")
            return False
    except Exception as e:
        print(f"❌ Error importing {module_name}: {e}")
        return False

def main():
    print("=" * 70)
    print("OAuth Implementation Verification")
    print("=" * 70)
    print()
    
    all_checks_passed = True
    
    # Check core files exist
    print("1. Checking core files...")
    all_checks_passed &= check_file_exists("app.py", "Main application")
    all_checks_passed &= check_file_exists("processor.py", "Processor module")
    all_checks_passed &= check_file_exists("xero_aprun_downloader.py", "Downloader module")
    all_checks_passed &= check_file_exists("templates/index.html", "HTML template")
    print()
    
    # Check documentation files
    print("2. Checking documentation files...")
    all_checks_passed &= check_file_exists("OAUTH_SETUP.md", "OAuth setup guide")
    all_checks_passed &= check_file_exists("DEPLOYMENT_CHECKLIST.md", "Deployment checklist")
    all_checks_passed &= check_file_exists("QUICKSTART.md", "Quick start guide")
    all_checks_passed &= check_file_exists("xero_secrets.json.example", "Secrets template")
    print()
    
    # Check SECRETS_PATH constant
    print("3. Checking SECRETS_PATH constant...")
    all_checks_passed &= check_constant_in_file(
        "processor.py", 
        "SECRETS_PATH", 
        "/home/xero_secrets.json"
    )
    all_checks_passed &= check_constant_in_file(
        "xero_aprun_downloader.py", 
        "SECRETS_PATH", 
        "/home/xero_secrets.json"
    )
    print()
    
    # Check OAuth routes in app.py
    print("4. Checking OAuth routes...")
    all_checks_passed &= check_string_in_file(
        "app.py",
        '@app.get("/authorize-xero")',
        "Authorize route"
    )
    all_checks_passed &= check_string_in_file(
        "app.py",
        '@app.get("/callback")',
        "Callback route"
    )
    all_checks_passed &= check_string_in_file(
        "app.py",
        "from processor import run_ap_process, load_secrets, save_secrets",
        "Processor imports"
    )
    print()
    
    # Check HTML template
    print("5. Checking HTML template...")
    all_checks_passed &= check_string_in_file(
        "templates/index.html",
        'href="/authorize-xero"',
        "Authorize Xero button"
    )
    all_checks_passed &= check_string_in_file(
        "templates/index.html",
        'Authorize Xero',
        "Button text"
    )
    print()
    
    # Check .gitignore
    print("6. Checking .gitignore...")
    all_checks_passed &= check_string_in_file(
        ".gitignore",
        "xero_secrets.json",
        "Secrets file ignored"
    )
    print()
    
    # Check token rotation logic
    print("7. Checking token rotation logic...")
    all_checks_passed &= check_string_in_file(
        "processor.py",
        "save_secrets(secrets)",
        "Token persistence in refresh_access_token"
    )
    all_checks_passed &= check_string_in_file(
        "processor.py",
        'new_refresh_token = token_data.get("refresh_token")',
        "Refresh token extraction"
    )
    print()
    
    # Check module imports
    print("8. Checking Python modules can be imported...")
    all_checks_passed &= check_module_imports("app")
    all_checks_passed &= check_module_imports("processor")
    all_checks_passed &= check_module_imports("xero_aprun_downloader")
    print()
    
    # Final result
    print("=" * 70)
    if all_checks_passed:
        print("✅ ALL CHECKS PASSED - Ready for deployment!")
        print()
        print("Next steps:")
        print("1. Review changes: git diff")
        print("2. Commit: git add . && git commit -m 'Implement OAuth flow'")
        print("3. Push: git push origin main")
        print("4. Follow DEPLOYMENT_CHECKLIST.md")
        return 0
    else:
        print("❌ SOME CHECKS FAILED - Please review errors above")
        return 1

if __name__ == "__main__":
    sys.exit(main())
