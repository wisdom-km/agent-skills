@echo off
rem Windows launcher. cmd and PowerShell cannot run the extension-less skill-map script.
rem Tries py -3, then python, then python3. A Store alias that exits 9009 is not Python.
rem The interpreter's exit code is this file's exit code. Nothing is written when none work.
set "SCRIPT=%~dp0skill_map.py"

py -3 -c "import sys; raise SystemExit(0 if sys.version_info[0]==3 else 1)" >nul 2>&1
if errorlevel 1 goto try_python
py -3 "%SCRIPT%" %*
exit /b %ERRORLEVEL%

:try_python
python -c "import sys; raise SystemExit(0 if sys.version_info[0]==3 else 1)" >nul 2>&1
if errorlevel 1 goto try_python3
python "%SCRIPT%" %*
exit /b %ERRORLEVEL%

:try_python3
python3 -c "import sys; raise SystemExit(0 if sys.version_info[0]==3 else 1)" >nul 2>&1
if errorlevel 1 goto fail
python3 "%SCRIPT%" %*
exit /b %ERRORLEVEL%

:fail
echo skill-map: no working Python 3 interpreter was found. On Windows, python3 is often a Store alias that exits 9009 and is not Python. Tried: py -3, python, python3. Nothing was written. 1>&2
exit /b 127
