@echo off
echo Starting FinComplaint AI Backend...
set PYTHONPATH=%cd%\backend
uvicorn backend.main:app --reload --port 8000
