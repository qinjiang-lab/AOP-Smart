@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ===============================
echo   AOP-Smart One-Click Runner
echo ===============================

:: ---------------------------
:: 1. Check Python
:: ---------------------------
echo [1] Checking Python environment...

set PYTHON_CMD=

python --version >nul 2>&1
if %errorlevel%==0 (
    set PYTHON_CMD=python
) else (
    python3 --version >nul 2>&1
    if %errorlevel%==0 (
        set PYTHON_CMD=python3
    )
)

if "%PYTHON_CMD%"=="" (
    echo [ERROR] Python not found. Please install Python first.
    pause
    exit /b
)

echo [OK] Using %PYTHON_CMD%

:: ---------------------------
:: 2. Check pip
:: ---------------------------
echo(
echo [2] Checking pip...

set PIP_CMD=

%PYTHON_CMD% -m pip --version >nul 2>&1
if %errorlevel%==0 (
    set PIP_CMD=%PYTHON_CMD% -m pip
) else (
    pip --version >nul 2>&1
    if %errorlevel%==0 (
        set PIP_CMD=pip
    ) else (
        pip3 --version >nul 2>&1
        if %errorlevel%==0 (
            set PIP_CMD=pip3
        )
    )
)

if "%PIP_CMD%"=="" (
    echo [ERROR] pip not found. Please install pip first.
    pause
    exit /b
)

echo [OK] pip is available

:: ---------------------------
:: 3. Check and install requirements.txt
:: ---------------------------
echo(
echo [3] Checking requirements.txt...

if exist "requirements.txt" (
    echo [INFO] requirements.txt found. Installing all dependencies...
    %PIP_CMD% install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install dependencies from requirements.txt!
        pause
        exit /b
    )
    echo [OK] All dependencies installed successfully
) else (
    echo [WARN] requirements.txt not found. Skipping batch install.
)

:: ---------------------------
:: 4. Check openai package (fallback check)
:: ---------------------------
echo(
echo [4] Checking openai package...

%PYTHON_CMD% -c "import openai" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] openai not installed. Installing...
    %PIP_CMD% install openai
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install openai!
        pause
        exit /b
    )
    echo [OK] openai installed successfully
) else (
    echo [OK] openai already installed
)

:: ---------------------------
:: 5. Check aop-wiki.xml
:: ---------------------------
echo(
echo [5] Checking aop-wiki.xml...

if not exist "aop-wiki.xml" (
    echo [ERROR] aop-wiki.xml not found in current directory!
    echo Please place it in this folder and try again.
    pause
    exit /b
)

echo [OK] aop-wiki.xml found

:: ---------------------------
:: 6. Check Index.txt
:: ---------------------------
echo(
echo [6] Checking Index.txt...

if not exist "Index.txt" (
    echo [INFO] Index.txt not found. Running XML_analysis.py...

    if not exist "XML_analysis.py" (
        echo [ERROR] XML_analysis.py not found!
        pause
        exit /b
    )

    %PYTHON_CMD% XML_analysis.py

    if %errorlevel% neq 0 (
        echo [ERROR] XML_analysis.py execution failed!
        pause
        exit /b
    )

    echo [OK] Index.txt generated
) else (
    echo [OK] Index.txt already exists. Skipping analysis.
)

:: ---------------------------
:: 7. Run main program
:: ---------------------------
echo(
echo [7] Running AOP-Smart.py...

if not exist "AOP-Smart.py" (
    echo [ERROR] AOP-Smart.py not found!
    pause
    exit /b
)

%PYTHON_CMD% AOP-Smart.py

echo ===============================
echo   Finished
echo ===============================
pause