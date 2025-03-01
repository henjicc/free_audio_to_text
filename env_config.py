#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
环境变量配置加载工具
从.env文件或系统环境变量加载配置
"""

import os
import sys
from pathlib import Path
from typing import Dict, Optional
from dotenv import load_dotenv

# 尝试从.env文件加载环境变量
load_dotenv()

class EnvConfig:
    """环境变量配置管理类"""
    
    @staticmethod
    def get_config() -> Dict[str, str]:
        """获取所有配置项"""
        config = {
            # 七牛云配置
            "QINIU_ACCESS_KEY": os.getenv("QINIU_ACCESS_KEY", ""),
            "QINIU_SECRET_KEY": os.getenv("QINIU_SECRET_KEY", ""),
            "QINIU_BUCKET_NAME": os.getenv("QINIU_BUCKET_NAME", ""),
            "QINIU_BUCKET_DOMAIN": os.getenv("QINIU_BUCKET_DOMAIN", ""),
            
            # 阿里云配置
            "ALIYUN_API_KEY": os.getenv("ALIYUN_API_KEY", ""),
            
            # API服务器配置
            "API_HOST": os.getenv("API_HOST", "0.0.0.0"),
            "API_PORT": os.getenv("API_PORT", "8000"),
        }
        return config
    
    @staticmethod
    def validate_config() -> bool:
        """验证必要的配置是否存在"""
        config = EnvConfig.get_config()
        
        # 检查七牛云配置
        qiniu_config_valid = all([
            config["QINIU_ACCESS_KEY"],
            config["QINIU_SECRET_KEY"],
            config["QINIU_BUCKET_NAME"],
            config["QINIU_BUCKET_DOMAIN"]
        ])
        
        # 检查阿里云配置
        aliyun_config_valid = bool(config["ALIYUN_API_KEY"])
        
        return qiniu_config_valid and aliyun_config_valid
    
    @staticmethod
    def print_status():
        """打印配置状态"""
        config = EnvConfig.get_config()
        
        print("\n🔑 配置状态:")
        print("-" * 40)
        
        # 七牛云配置
        print("七牛云配置:")
        print(f"  Access Key: {'已配置 ✅' if config['QINIU_ACCESS_KEY'] else '未配置 ❌'}")
        print(f"  Secret Key: {'已配置 ✅' if config['QINIU_SECRET_KEY'] else '未配置 ❌'}")
        print(f"  Bucket 名称: {'已配置 ✅' if config['QINIU_BUCKET_NAME'] else '未配置 ❌'}")
        print(f"  Bucket 域名: {'已配置 ✅' if config['QINIU_BUCKET_DOMAIN'] else '未配置 ❌'}")
        
        # 阿里云配置
        print("\n阿里云配置:")
        print(f"  API Key: {'已配置 ✅' if config['ALIYUN_API_KEY'] else '未配置 ❌'}")
        
        print("-" * 40)
        print(f"配置状态: {'所有配置有效 ✅' if EnvConfig.validate_config() else '配置不完整 ⚠️'}")
        print("")

# 获取指定配置项
def get_config(key: str, default: Optional[str] = None) -> str:
    """获取指定的配置项，如不存在则返回默认值"""
    config = EnvConfig.get_config()
    return config.get(key, default)

if __name__ == "__main__":
    # 如果直接运行此脚本，则打印配置状态
    EnvConfig.print_status() 