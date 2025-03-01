#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
音频下载工具
使用yt-dlp从网络链接下载音频文件
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

def download_audio(url, output_dir=None, verbose=False):
    """
    从URL下载音频文件
    
    参数:
        url: 要下载的音频URL
        output_dir: 输出目录，默认为当前目录下的临时文件夹
        verbose: 是否显示详细输出
        
    返回:
        success: 布尔值，表示是否下载成功
        output_file: 下载的文件路径
    """
    # 检查URL是否为空
    if not url:
        if verbose:
            print("❌ 错误: URL不能为空")
        return False, None
    
    # 如果未指定输出目录，则在当前目录创建临时文件夹
    if not output_dir:
        current_dir = os.getcwd()
        output_dir = os.path.join(current_dir, "downloads_temp")
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 构建yt-dlp命令
    cmd = [
        "yt-dlp",
        "-x",  # 提取音频
        "-o", f"{output_dir}/%(title)s.%(ext)s",  # 设置输出文件名
        url  # 下载链接
    ]
    
    if verbose:
        print(f"📥 正在下载: {url}")
        print(f"📂 输出目录: {output_dir}")
    
    try:
        # 执行yt-dlp命令
        if verbose:
            # 显示详细输出
            result = subprocess.run(cmd, check=True)
        else:
            # 隐藏详细输出
            result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # 查找生成的文件
        # 获取下载目录中最新的文件
        files = list(Path(output_dir).glob("*.*"))
        if files:
            # 按修改时间排序，获取最新的文件
            latest_file = max(files, key=os.path.getmtime)
            if verbose:  # 只在verbose模式下显示
                print(f"✅ 下载成功: {os.path.basename(latest_file)}")
            return True, str(latest_file)
        else:
            if verbose:  # 只在verbose模式下显示
                print("❌ 下载失败: 未找到下载的文件")
            return False, None
            
    except subprocess.CalledProcessError as e:
        if verbose:  # 只在verbose模式下显示
            print(f"❌ 下载失败: yt-dlp命令执行错误 (退出码: {e.returncode})")
            if e.stderr:
                print(f"错误信息: {e.stderr.decode('utf-8', errors='replace')}")
        return False, None
    except Exception as e:
        if verbose:  # 只在verbose模式下显示
            print(f"❌ 下载失败: {str(e)}")
        return False, None

def main():
    """主函数，处理命令行参数并下载音频"""
    # 创建参数解析器
    parser = argparse.ArgumentParser(description="从URL下载音频文件")
    parser.add_argument("url", help="要下载的音频URL")
    parser.add_argument("-o", "--output-dir", help="输出目录路径")
    parser.add_argument("-v", "--verbose", action="store_true", help="显示详细输出")
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 下载音频
    success, output_file = download_audio(
        args.url, 
        args.output_dir, 
        args.verbose
    )
    
    if success:
        if args.verbose:  # 只在verbose模式下显示
            print(f"📋 文件路径: {output_file}")
        else:
            # 在非verbose模式下只输出文件路径（不带提示）
            print(output_file)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main() 