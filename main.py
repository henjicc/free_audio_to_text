#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
音频处理工作流工具
整合下载、上传和语音识别的完整流程
"""

import os
import sys
import argparse
import tempfile
import shutil  # 用于删除目录
from typing import Dict, Any, Tuple, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 导入功能模块
from download_audio import download_audio
from qiniu_upload import QiniuUploader
from aliyun_speech_recognition import AliyunSpeechRecognition
from qiniu import BucketManager, Auth  # 添加BucketManager用于删除云端文件

def process_audio(
    url: str, 
    output_dir: Optional[str] = None,
    language: str = 'auto',
    keep_tags: bool = False,
    link_expires: int = 3600,
    verbose: bool = False,
    save_json: Optional[str] = None,
    cleanup: bool = False,
    # 参数用于覆盖环境变量
    qiniu_access_key: Optional[str] = None,
    qiniu_secret_key: Optional[str] = None,
    qiniu_bucket_name: Optional[str] = None,
    qiniu_bucket_domain: Optional[str] = None,
    aliyun_api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    完整的音频处理工作流：下载 -> 上传 -> 识别 -> 清理
    
    参数:
        url: 要处理的音频URL
        output_dir: 音频下载的临时目录
        language: 语音识别的语言代码
        keep_tags: 是否保留情感和音频事件标记
        link_expires: 七牛云下载链接的有效期(秒)
        verbose: 是否显示详细信息
        save_json: 保存识别结果的JSON文件路径
        cleanup: 处理完成后是否清理临时文件和云端文件
        qiniu_access_key: 七牛云访问密钥
        qiniu_secret_key: 七牛云密钥
        qiniu_bucket_name: 七牛云存储桶名称
        qiniu_bucket_domain: 七牛云存储桶域名
        aliyun_api_key: 阿里云API密钥
        
    返回:
        处理结果字典
    """
    result = {
        "success": False,
        "steps_completed": [],
        "error": None
    }
    
    # 创建临时目录用于下载文件
    if not output_dir:
        output_dir = os.path.join(os.getcwd(), "downloads_temp")
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # ==== 步骤1: 下载音频 ====
    if verbose:
        print("\n🔄 步骤1: 下载音频...")
    
    try:
        download_success, audio_file = download_audio(url, output_dir, verbose)
        
        if not download_success or not audio_file:
            result["error"] = f"下载音频失败: {audio_file if audio_file else '未知错误'}"
            return result
            
        result["steps_completed"].append("download")
        result["audio_file"] = audio_file
        
        if verbose:
            print(f"✅ 音频下载成功: {audio_file}")
    
    except Exception as e:
        result["error"] = f"下载音频过程出错: {str(e)}"
        return result
    
    # 重要：存储云端文件标识，后续清理时需要使用
    cloud_file_key = None
    
    # ==== 步骤2: 上传到七牛云 ====
    if verbose:
        print("\n🔄 步骤2: 上传到七牛云...")
    
    try:
        # 获取七牛云配置(优先级：参数 > 环境变量)
        access_key = qiniu_access_key or os.environ.get("QINIU_ACCESS_KEY")
        secret_key = qiniu_secret_key or os.environ.get("QINIU_SECRET_KEY") 
        bucket_name = qiniu_bucket_name or os.environ.get("QINIU_BUCKET_NAME")
        bucket_domain = qiniu_bucket_domain or os.environ.get("QINIU_BUCKET_DOMAIN")
        
        # 检查配置是否完整
        if not all([access_key, secret_key, bucket_name, bucket_domain]):
            result["error"] = "七牛云配置不完整，请设置环境变量或通过参数提供配置"
            return result
            
        # 创建上传器
        uploader = QiniuUploader(access_key, secret_key, bucket_name, bucket_domain)
        
        # 上传文件
        upload_success, upload_result = uploader.upload_file(audio_file, None, link_expires)
        
        if not upload_success:
            result["error"] = f"上传到七牛云失败: {upload_result}"
            return result
            
        result["steps_completed"].append("upload")
        result["upload_result"] = upload_result
        result["download_url"] = upload_result["direct_link"]
        
        # 保存文件标识用于后续删除
        cloud_file_key = upload_result["file_key"]
        result["cloud_file_key"] = cloud_file_key
        
        if verbose:
            print(f"✅ 文件上传成功")
            print(f"📋 下载链接: {upload_result['direct_link']}")
            print(f"⏱️ 链接有效期: {upload_result['expires']} 秒")
    except Exception as e:
        result["error"] = f"上传到七牛云过程出错: {str(e)}"
        return result
    
    # ==== 步骤3: 阿里云语音识别 ====
    if verbose:
        print("\n🔄 步骤3: 阿里云语音识别...")
    
    try:
        # 初始化语音识别工具
        recognizer = AliyunSpeechRecognition(remove_tags=not keep_tags)
        
        # 执行语音识别
        recognition_result = recognizer.recognize_file(
            file_url=result["download_url"],
            language=language,
            verbose=verbose
        )
        
        if "error" in recognition_result:
            result["error"] = f"语音识别失败: {recognition_result['error']}"
            return result
            
        result["steps_completed"].append("recognition")
        result["recognition_result"] = recognition_result
        result["text"] = recognition_result["text"]
        if "original_text" in recognition_result:
            result["original_text"] = recognition_result["original_text"]
            
        # 保存JSON结果
        if save_json:
            try:
                import json
                with open(save_json, 'w', encoding='utf-8') as f:
                    json.dump(recognition_result, f, ensure_ascii=False, indent=2)
                if verbose:
                    print(f"✅ 识别结果已保存至: {save_json}")
            except Exception as e:
                if verbose:
                    print(f"❌ 保存结果失败: {str(e)}")
        
    except Exception as e:
        result["error"] = f"语音识别过程出错: {str(e)}"
        return result
    
    # 所有步骤完成
    result["success"] = True
    
    # ==== 步骤4: 清理文件 ====
    if cleanup and result["success"]:
        if verbose:
            print("\n🔄 步骤4: 清理临时文件和云端文件...")
        
        # 4.1 清理云端文件
        try:
            if cloud_file_key:
                # 创建鉴权对象和BucketManager
                q = Auth(access_key, secret_key)
                bucket_manager = BucketManager(q)
                
                # 删除云端文件
                delete_ret, delete_info = bucket_manager.delete(bucket_name, cloud_file_key)
                
                if delete_info.status_code == 200:
                    result["steps_completed"].append("cloud_cleanup")
                    if verbose:
                        print(f"✅ 已删除云端文件: {cloud_file_key}")
                else:
                    if verbose:
                        print(f"⚠️ 云端文件删除失败: {delete_info.text_body}")
        except Exception as e:
            if verbose:
                print(f"⚠️ 云端文件删除出错: {str(e)}")
        
        # 4.2 清理本地文件
        try:
            # 删除单个文件
            if "audio_file" in result and os.path.exists(result["audio_file"]):
                os.remove(result["audio_file"])
                
                # 检查临时目录是否为空，如果为空则删除目录
                if output_dir and os.path.exists(output_dir) and not os.listdir(output_dir):
                    shutil.rmtree(output_dir)
                
                result["steps_completed"].append("local_cleanup")
                if verbose:
                    print(f"✅ 已删除本地临时文件和目录")
        except Exception as e:
            if verbose:
                print(f"⚠️ 本地文件清理出错: {str(e)}")
    
    return result

def main():
    """主函数，处理命令行参数并执行工作流"""
    # 创建参数解析器
    parser = argparse.ArgumentParser(description="音频处理工作流：下载 -> 上传 -> 识别 -> 清理")
    parser.add_argument("url", help="要处理的音频URL")
    parser.add_argument("-o", "--output-dir", help="音频下载的临时目录")
    parser.add_argument("-l", "--language", default="auto", help="语音识别的语言代码，默认为auto自动检测")
    parser.add_argument("--keep-tags", action="store_true", help="保留情感和音频事件标记")
    parser.add_argument("-e", "--expires", type=int, default=3600, help="七牛云下载链接的有效期(秒)，默认3600")
    parser.add_argument("-v", "--verbose", action="store_true", help="显示详细处理信息")
    parser.add_argument("-s", "--save", help="保存识别结果的JSON文件路径")
    parser.add_argument("--no-cleanup", action="store_true", help="不清理临时文件和云端文件")
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 执行工作流 - 默认开启cleanup (通过反转no-cleanup参数)
    result = process_audio(
        url=args.url,
        output_dir=args.output_dir,
        language=args.language,
        keep_tags=args.keep_tags,
        link_expires=args.expires,
        verbose=args.verbose,
        save_json=args.save,
        cleanup=not args.no_cleanup  # 默认启用清理
    )
    
    # 处理结果
    if not result["success"]:
        if args.verbose:
            print(f"\n❌ 处理失败: {result['error']}")
            print(f"📊 已完成步骤: {', '.join(result['steps_completed'])}")
        sys.exit(1)
    
    # 如果是详细模式，显示带格式的识别文本
    if args.verbose:
        print("\n📝 识别结果:")
        print("-" * 60)
        print(result["text"])
        print("-" * 60)
        
        # 如果保留了标记，显示原始文本
        if args.keep_tags and "original_text" in result:
            print("\n📝 原始识别结果 (包含标记):")
            print("-" * 60)
            print(result["original_text"])
            print("-" * 60)
            
        # 添加清理步骤信息输出
        cleanup_steps = [step for step in result["steps_completed"] if step in ("cloud_cleanup", "local_cleanup")]
        if cleanup_steps:
            print(f"🧹 已完成清理: {', '.join(cleanup_steps)}")
        
        print(f"\n✅ 处理完成! 共完成 {len(result['steps_completed'])} 个步骤")
    else:
        # 非详细模式，只输出纯文本结果
        print(result["text"])
    
if __name__ == "__main__":
    main() 