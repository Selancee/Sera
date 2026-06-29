@echo off
setlocal
cd /d D:\Sera
if not exist .venv (
  python -m venv .venv
)
call .venv\Scripts\activate.bat
if "%SERA_SYMBOLIC_MODEL_DIR%"=="" set SERA_SYMBOLIC_MODEL_DIR=%CD%\models\sera_symbolic_small
if "%SERA_GENERATOR_BACKEND%"=="" set SERA_GENERATOR_BACKEND=model
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload
