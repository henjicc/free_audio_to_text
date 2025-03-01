#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
七牛云文件上传工具
实现文件上传并获取直链功能
"""

import os
import sys
import time
from qiniu import Auth, put_file, etag
import qiniu.config

# 尝试导入配置文件
try:
    import config
    config_exists = True
except ImportError:
    config_exists = False

class QiniuUploader:
    def __init__(self, access_key, secret_key, bucket_name, bucket_domain):
        """
        初始化上传器
        
        参数:
            access_key: 七牛云Access Key
            secret_key: 七牛云Secret Key
            bucket_name: 存储空间名称
            bucket_domain: 存储空间绑定的域名(不含http://)
        """
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        self.bucket_domain = bucket_domain
        # 构建鉴权对象
        self.q = Auth(access_key, secret_key)
    
    def get_upload_token(self, key=None, expires=3600):
        """
        获取上传凭证
        
        参数:
            key: 文件名
            expires: 凭证有效期(秒)
            
        返回:
            upload_token: 上传凭证
        """
        # 生成上传Token
        token = self.q.upload_token(self.bucket_name, key, expires)
        return token
    
    def get_download_url(self, file_key, expires=3600):
        """
        获取带签名的下载链接
        
        参数:
            file_key: 文件标识
            expires: 链接有效期(秒)
            
        返回:
            download_url: 带签名的下载链接
        """
        # 构建基本URL
        base_url = f'http://{self.bucket_domain}/{file_key}'
        # 生成带签名的下载链接
        private_url = self.q.private_download_url(base_url, expires=expires)
        return private_url
    
    def upload_file(self, local_file, remote_name=None, expires=3600):
        """
        上传文件到七牛云
        
        参数:
            local_file: 本地文件路径
            remote_name: 远程文件名，不指定则使用本地文件名
            expires: 生成的下载链接有效期(秒)
            
        返回:
            success: 布尔值，表示是否上传成功
            result: 上传结果信息，成功时包含直链
        """
        # 检查文件是否存在
        if not os.path.isfile(local_file):
            return False, "文件不存在：" + local_file
        
        # 如果未指定远程文件名，则使用本地文件名
        if remote_name is None:
            remote_name = os.path.basename(local_file)
        
        # 添加时间戳前缀，避免文件名冲突
        timestamp = int(time.time())
        remote_name = f"{timestamp}_{remote_name}"
        
        # 获取上传凭证
        token = self.get_upload_token(remote_name)
        
        # 执行上传操作
        try:
            ret, info = put_file(token, remote_name, local_file)
            # 检查上传是否成功
            if info.status_code == 200:
                # 生成带签名的下载链接
                download_url = self.get_download_url(remote_name, expires)
                
                return True, {
                    "direct_link": download_url,
                    "file_key": remote_name,
                    "hash": ret.get("hash", ""),
                    "expires": expires,
                    "info": info
                }
            else:
                return False, f"上传失败: {info}"
        except Exception as e:
            return False, f"上传过程出错: {str(e)}"

def main():
    """主函数，处理命令行参数并执行上传"""
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("使用方法: python qiniu_upload.py <本地文件路径> [远程文件名] [链接有效期(秒)]")
        return
    
    # 获取命令行参数
    local_file = sys.argv[1]
    remote_name = sys.argv[2] if len(sys.argv) > 2 else None
    expires = int(sys.argv[3]) if len(sys.argv) > 3 else 3600  # 默认有效期1小时
    
    # 获取七牛云配置
    if config_exists:
        # 从配置文件读取
        access_key = config.QINIU_ACCESS_KEY
        secret_key = config.QINIU_SECRET_KEY
        bucket_name = config.QINIU_BUCKET_NAME
        bucket_domain = config.QINIU_BUCKET_DOMAIN
    else:
        # 从环境变量读取(作为备选)
        access_key = os.environ.get("QINIU_ACCESS_KEY", "")
        secret_key = os.environ.get("QINIU_SECRET_KEY", "")
        bucket_name = os.environ.get("QINIU_BUCKET_NAME", "")
        bucket_domain = os.environ.get("QINIU_BUCKET_DOMAIN", "")
    
    # 检查配置是否完整
    if not all([access_key, secret_key, bucket_name, bucket_domain]):
        if not config_exists:
            print("❌ 错误: 未找到config.py配置文件")
            print("请创建config.py文件并填写七牛云账号信息，参考格式如下:")
            print("-" * 50)
            print('QINIU_ACCESS_KEY = "您的Access Key"')
            print('QINIU_SECRET_KEY = "您的Secret Key"')
            print('QINIU_BUCKET_NAME = "您的存储空间名称"')
            print('QINIU_BUCKET_DOMAIN = "您的存储空间域名"')
            print("-" * 50)
        else:
            print("❌ 错误: 配置信息不完整，请在config.py中填写所有必要的信息")
        return
    
    # 创建上传器
    uploader = QiniuUploader(access_key, secret_key, bucket_name, bucket_domain)
    
    # 上传文件
    success, result = uploader.upload_file(local_file, remote_name, expires)
    
    # 输出结果
    if success:
        print("✅ 文件上传成功！")
        print(f"📋 带签名的下载链接: {result['direct_link']}")
        print(f"⏱️ 链接有效期: {result['expires']} 秒")
        print(f"🔑 文件标识: {result['file_key']}")
        print(f"🔐 文件哈希: {result['hash']}")
    else:
        print(f"❌ 上传失败: {result}")

if __name__ == "__main__":
    main() 