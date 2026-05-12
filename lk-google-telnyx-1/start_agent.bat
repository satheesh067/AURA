@echo off
echo ========================================
echo Voice Agent Backend (LiveKit)
echo ========================================
echo.

echo Starting Voice Agent...
echo Keep this window open!
echo.

REM Activate virtual environment
call .venv\Scripts\activate.bat

echo Waiting for agent to register with LiveKit...
echo.

REM Start the LiveKit agent
python src/agent.py start

pause
