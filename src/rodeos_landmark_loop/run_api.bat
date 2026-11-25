@echo off
call conda activate rodeos-analysis
python -m uvicorn rodeos_loop.api:app --host 127.0.0.1 --port 8001
