@echo off
chcp 65001 >nul
setlocal

echo =========================================
echo 文件夹比较工具启动器
echo =========================================

REM 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误：未检测到Python安装！
    echo 请先安装Python，然后再运行此程序。
    echo 您可以从 https://www.python.org/downloads/ 下载Python
    pause
    exit /b 1
)

REM 检查pip是否可用
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误：pip不可用！
    echo 请确保Python安装时包含了pip，或手动安装pip。
    pause
    exit /b 1
)

REM 安装依赖
pip install -r requirements.txt >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误：安装依赖失败！
    echo 正在尝试以详细模式安装依赖...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo 安装依赖失败，请检查网络连接或手动安装。
        pause
        exit /b 1
    )
)

REM 运行程序
echo 正在启动文件夹比较工具...
python folder-comparator-gui.py

REM 检查程序是否正常结束
if %errorlevel% neq 0 (
    echo 程序异常退出，错误代码：%errorlevel%
    echo 请检查是否有依赖缺失或其他问题。
    pause
    exit /b %errorlevel%
)

endlocal