@echo off
chcp 65001 >nul

echo ========================================
echo           启动应用程序
echo ========================================
echo.

REM 检查环境
if not exist "venv\Scripts\activate.bat" (
    echo [错误] 未找到虚拟环境
    pause
    exit /b 1
)

if not exist "app.py" (
    echo [错误] 未找到 app.py 文件
    pause
    exit /b 1
)

REM 激活虚拟环境并启动应用
call venv\Scripts\activate.bat

REM 生成 5000-9999 范围内的随机端口
set /a min_port=5000
set /a max_port=9999
set /a port_range=%max_port% - %min_port% + 1

REM 使用 %RANDOM% 生成随机端口
set /a random_port=%RANDOM% %% %port_range% + %min_port%

echo [信息] 应用启动中...
echo    访问地址: http://127.0.0.1:%random_port%
echo    关闭此窗口即停止服务
echo ========================================
echo.

REM 在新窗口中打开浏览器
start http://127.0.0.1:%random_port%

REM 直接运行 Python 应用（窗口关闭时进程自动结束）
start /B python app.py --port=%random_port%

echo.
echo [信息] 服务已停止
pause
