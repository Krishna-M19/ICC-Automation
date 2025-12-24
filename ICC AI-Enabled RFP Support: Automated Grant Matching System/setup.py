"""
Create Windows batch file for running the RFP Production System
One-time utility
"""
from pathlib import Path


def create_batch_file():
    project_root = Path(__file__).parent
    batch_path = project_root / "run_rfp_production.bat"

    batch_content = f"""@echo off
REM RFP Production System - Automated Execution
REM Michigan Technological University

cd /d "{project_root}"

echo Starting RFP Production System...
echo Time: %date% %time%

python main.py

echo.
echo RFP Production System completed.
echo Time: %date% %time%

REM Uncomment to keep the window open
REM pause
"""

    with open(batch_path, "w", encoding="utf-8") as f:
        f.write(batch_content)

    print(" Batch file created successfully:")
    print(f"   {batch_path}")


if __name__ == "__main__":
    try:
        create_batch_file()
    except Exception as e:
        print(f"Failed to create batch file: {e}")
