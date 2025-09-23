@echo off
chcp 65001
echo ========================================
echo 抖音直播弹幕采集工具 - 一键打包脚本
echo ========================================

echo 正在检查Python环境...
python --version
if errorlevel 1 (
    echo 错误: 未找到Python环境，请先安装Python
    pause
    exit /b 1
)

echo.
echo 正在检查Node.js环境...
node --version >nul 2>&1
if errorlevel 1 (
    echo 警告: 未检测到Node.js，将使用py_mini_racer作为JavaScript引擎
) else (
    echo 检测到Node.js环境
)

echo.
echo 正在安装依赖包...
pip install pyinstaller>=5.0
pip install openpyxl>=3.0.0
pip install websocket-client>=1.6.0
pip install py-mini-racer>=0.6.0
pip install requests>=2.25.0
pip install certifi>=2021.5.25

echo.
echo 开始打包程序...
pyinstaller --name="抖音直播弹幕采集工具" ^
    --onefile ^
    --windowed ^
    --add-data="protobuf;protobuf" ^
    --add-data="sign.js;." ^
    --hidden-import=openpyxl ^
    --hidden-import=websocket ^
    --hidden-import=py_mini_racer ^
    --hidden-import=py_mini_racer.py_mini_racer ^
    --hidden-import=ssl ^
    --hidden-import=certifi ^
    --hidden-import=base64 ^
    --collect-all=openpyxl ^
    --collect-all=websocket ^
    --collect-all=certifi ^
    --collect-all=py_mini_racer ^
    ui_main.py

if errorlevel 1 (
    echo 打包失败！
    pause
    exit /b 1
)

echo.
echo ========================================
echo 打包完成！
echo 可执行文件位置: dist\抖音直播弹幕采集工具.exe
echo.
echo 注意事项:
echo - 程序已集成py_mini_racer，无需Node.js环境
echo - 如果运行时出现签名问题，程序会自动使用备用算法
echo ========================================
pause
