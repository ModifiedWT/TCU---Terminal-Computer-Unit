@echo off
REM Builds a standalone Windows .exe using PyInstaller.
REM Run from the project root: build.bat

echo Installing PyInstaller...
pip install pyinstaller --quiet
if errorlevel 1 (
    echo.
    echo FAILED: pip install pyinstaller did not succeed. See errors above.
    pause
    exit /b 1
)

echo.
echo Building PDAWidget.exe...
pyinstaller ^
  --noconsole ^
  --onefile ^
  --name "PDAWidget" ^
  --add-data "style_template.qss;ui" ^
  main.py

if errorlevel 1 (
    echo.
    echo FAILED: PyInstaller reported an error. Scroll up to see it.
    pause
    exit /b 1
)

if not exist "dist\PDAWidget.exe" (
    echo.
    echo FAILED: build finished with no error, but dist\PDAWidget.exe was not created.
    pause
    exit /b 1
)

echo.
echo SUCCESS: dist\PDAWidget.exe was created.
pause