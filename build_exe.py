#!/usr/bin/python
# coding:utf-8

# @FileName:    build_exe.py
# @Time:        2024/1/2 22:27
# @Author:      bubu
# @Project:     douyinLiveWebFetcher

"""
Windows可执行程序打包脚本
使用PyInstaller将Python程序打包成exe文件
"""

import os
import subprocess
import sys
import shutil
from pathlib import Path

def check_nodejs():
    """检查Node.js环境"""
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✓ 检测到Node.js: {result.stdout.strip()}")
            return True
        else:
            print("✗ Node.js未安装或不可用")
            return False
    except Exception as e:
        print(f"✗ Node.js检查失败: {e}")
        return False

def install_pyinstaller():
    """安装PyInstaller"""
    print("正在安装PyInstaller...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    print("PyInstaller安装完成!")

def install_requirements():
    """安装所有必要的依赖"""
    print("正在安装项目依赖...")
    requirements = [
        "pyinstaller>=5.0",
        "openpyxl>=3.0.0",
        "websocket-client>=1.6.0",
        "py-mini-racer>=0.6.0",  # 这个很重要，用于替代Node.js
        "requests>=2.25.0",
        "certifi>=2021.5.25"
    ]

    for req in requirements:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", req])
            print(f"✓ 已安装: {req}")
        except subprocess.CalledProcessError as e:
            print(f"✗ 安装失败: {req} - {e}")

def build_exe():
    """打包可执行文件"""
    print("开始打包可执行程序...")

    # 确保在正确的目录
    os.chdir(Path(__file__).parent)

    # PyInstaller打包命令
    cmd = [
        "pyinstaller",
        "--name=抖音直播弹幕采集工具",  # 可执行文件名称
        "--onefile",  # 打包成单个exe文件
        "--windowed",  # 无控制台窗口（GUI程序）
        "--add-data=protobuf;protobuf",  # 添加protobuf目录
        "--add-data=sign.js;.",  # 添加签名文件
        "--hidden-import=openpyxl",  # 确保openpyxl被包含
        "--hidden-import=websocket",  # 确保websocket被包含
        "--hidden-import=py_mini_racer",  # 确保py_mini_racer被包含
        "--hidden-import=py_mini_racer.py_mini_racer",  # 添加完整路径
        "--hidden-import=ssl",  # 添加ssl模块
        "--hidden-import=certifi",  # 添加证书模块
        "--hidden-import=base64",  # 添加base64模块
        "--collect-all=openpyxl",  # 收集openpyxl的所有依赖
        "--collect-all=websocket",  # 收集websocket的所有依赖
        "--collect-all=certifi",  # 收集证书文件
        "--collect-all=py_mini_racer",  # 收集py_mini_racer的所有依赖
        "--icon=icon.ico",  # 程序图标（如果有的话）
        "ui_main.py"  # 主程序文件
    ]

    try:
        subprocess.run(cmd, check=True)
        print("打包完成!")
        print("可执行文件位置: dist/抖音直播弹幕采集工具.exe")
        print("\n注意事项:")
        print("- 程序已集成py_mini_racer，无需额外的Node.js环境")
        print("- 如果运行时出现签名问题，程序会自动使用备用算法")
        print("- 建议在目标机器上测试运行效果")
    except subprocess.CalledProcessError as e:
        print(f"打包失败: {e}")
        return False

    return True

def build_dir_version():
    """打包成目录版本（包含所有依赖文件）"""
    print("开始打包目录版本...")

    # 确保在正确的目录
    os.chdir(Path(__file__).parent)

    # PyInstaller打包命令（目录版本）
    cmd = [
        "pyinstaller",
        "--name=抖音直播弹幕采集工具",
        "--onedir",  # 打包成目录
        "--windowed",  # 无控制台窗口
        "--add-data=protobuf;protobuf",
        "--add-data=sign.js;.",
        "--hidden-import=openpyxl",
        "--hidden-import=websocket",
        "--hidden-import=py_mini_racer",
        "--hidden-import=py_mini_racer.py_mini_racer",
        "--hidden-import=ssl",
        "--hidden-import=certifi",
        "--hidden-import=base64",
        "--collect-all=openpyxl",
        "--collect-all=websocket",
        "--collect-all=certifi",
        "--collect-all=py_mini_racer",
        "--icon=icon.ico",
        "ui_main.py"
    ]

    try:
        subprocess.run(cmd, check=True)
        print("目录版本打包完成!")
        print("程序目录位置: dist/抖音直播弹幕采集工具/")
    except subprocess.CalledProcessError as e:
        print(f"打包失败: {e}")
        return False

    return True

def create_spec_file():
    """创建自定义的spec文件"""
    spec_content = """
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['ui_main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('protobuf', 'protobuf'),
        ('sign.js', '.'),
    ],
    hiddenimports=[
        'openpyxl',
        'websocket',
        'py_mini_racer',
        'py_mini_racer.py_mini_racer',
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.filedialog',
        'tkinter.scrolledtext',
        'ssl',
        'certifi',
        'base64',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='抖音直播弹幕采集工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico'
)
"""

    with open("抖音直播弹幕采集工具.spec", "w", encoding="utf-8") as f:
        f.write(spec_content)

    print("已创建自定义spec文件: 抖音直播弹幕采集工具.spec")

def clean_build():
    """清理构建文件"""
    print("清理构建文件...")
    dirs_to_remove = ['build', 'dist', '__pycache__']
    files_to_remove = ['*.spec']

    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"已删除目录: {dir_name}")

    # 删除spec文件
    for spec_file in Path('.').glob('*.spec'):
        spec_file.unlink()
        print(f"已删除文件: {spec_file}")

def main():
    """主函数"""
    print("=== 抖音直播弹幕采集工具 - 打包程序 ===")
    print("📋 环境检查:")
    print(f"   Python版本: {sys.version}")
    nodejs_available = check_nodejs()
    if not nodejs_available:
        print("   ⚠️  Node.js不可用，将使用py_mini_racer作为JavaScript引擎")
    print()

    print("1. 清理并重新打包")
    print("2. 仅打包单文件版本")
    print("3. 仅打包目录版本")
    print("4. 创建自定义spec文件")
    print("5. 清理构建文件")
    print("6. 安装所有依赖")

    choice = input("请选择操作 (1-6): ").strip()

    if choice == "1":
        clean_build()
        install_requirements()

        if build_exe():
            print("\n单文件版本打包完成!")
            print("可执行文件: dist/抖音直播弹幕采集工具.exe")

        if build_dir_version():
            print("\n目录版本打包完成!")
            print("程序目录: dist/抖音直播弹幕采集工具/")

    elif choice == "2":
        build_exe()

    elif choice == "3":
        build_dir_version()

    elif choice == "4":
        create_spec_file()

    elif choice == "5":
        clean_build()

    elif choice == "6":
        install_requirements()

    else:
        print("无效选择")

if __name__ == "__main__":
    main()
