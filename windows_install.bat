@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo         Python 环境检测与虚拟环境安装
echo ========================================
echo.

REM 检测 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 当前系统未安装 Python，请安装 Python 环境
    pause
    exit /b 1
)

REM 获取 Python 版本号
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set PYTHON_MAJOR=%%a
    set PYTHON_MINOR=%%b
)

REM 检查 Python 版本是否大于 3.10
if %PYTHON_MAJOR% LSS 3 (
    echo [错误] 当前 Python 版本过低 ^(%PYTHON_VERSION%^)，请安装 Python 3.10 或更高版本
    pause
    exit /b 1
)
if %PYTHON_MAJOR% EQU 3 if %PYTHON_MINOR% LSS 10 (
    echo [错误] 当前 Python 版本过低 ^(%PYTHON_VERSION%^)，请安装 Python 3.10 或更高版本
    pause
    exit /b 1
)

echo [信息] 当前 Python 版本: %PYTHON_VERSION% (符合要求)
echo.

REM 创建虚拟环境
echo [信息] 正在创建虚拟环境 venv...
python -m venv venv
if errorlevel 1 (
    echo [错误] 创建虚拟环境失败，请检查 Python 安装
    pause
    exit /b 1
)
echo [信息] 虚拟环境创建成功
echo.

REM 激活虚拟环境并安装依赖
echo [信息] 正在激活虚拟环境并安装 requirements.txt...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [错误] 激活虚拟环境失败
    pause
    exit /b 1
)

REM 检查 requirements.txt 是否存在
if not exist requirements.txt (
    echo [警告] 未找到 requirements.txt 文件，跳过依赖安装
) else (
    echo [信息] 正在使用清华源安装依赖包...
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    if errorlevel 1 (
        echo [错误] 依赖包安装失败，请检查网络或 requirements.txt 内容
        pause
        exit /b 1
    )
    echo [信息] 依赖包安装完成
)

echo.
echo ========================================
echo [成功] 软件初始化成功！
echo ========================================
pause
