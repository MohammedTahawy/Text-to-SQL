#!/usr/bin/env python3
"""
==============================================================================
Executive Text-to-SQL AI Copilot - One-Click Demo Runner
Author: Mohamed Tahawy (https://github.com/MohammedTahawy)
Usage:
    python run_demo.py
==============================================================================
"""

import os
import sys
import shutil
import subprocess

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)

    print("\n" + "="*70)
    print("  🚀 Executive Text-to-SQL AI Copilot • Enterprise Multi-Tenant Engine")
    print("  Developed by: Mohamed Tahawy")
    print("="*70 + "\n")

    # 1. Ensure .env file exists
    env_file = os.path.join(base_dir, ".env")
    env_example = os.path.join(base_dir, ".env.example")
    if not os.path.exists(env_file) and os.path.exists(env_example):
        shutil.copy(env_example, env_file)
        print("[+] Created .env from .env.example")

    # 2. Ensure demo SQLite database exists
    db_file = os.path.join(base_dir, "demo_enterprise.db")
    if not os.path.exists(db_file):
        print("[*] Generating synthetic multi-tenant demo database...")
        from seed_demo_data import seed_database
        seed_database(base_dir)

    print("[✓] Environment and demo database ready.")
    print("[*] Starting FastAPI Server via Uvicorn on http://localhost:8000 ...")
    print("[*] Interactive Executive Dashboard: http://localhost:8000/demo")
    print("[*] Interactive API Swagger Docs:   http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop the server.\n" + "-"*70 + "\n")

    try:
        import uvicorn
        uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
    except ImportError:
        print("[!] Uvicorn not installed. Please run: pip install -r requirements.txt")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[✓] Server gracefully stopped.")

if __name__ == "__main__":
    main()
