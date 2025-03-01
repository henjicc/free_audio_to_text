#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
音频处理与语音识别 API 服务
使用 FastAPI 提供基于 HTTP 的服务接口
"""

import os
import sys
import json
from typing import Optional, Dict, Any
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, HttpUrl, Field

# 导入功能模块
from download_audio import download_audio
from qiniu_upload import QiniuUploader
from aliyun_speech_recognition import AliyunSpeechRecognition
from main import process_audio

# 创建 FastAPI 应用
app = FastAPI(
    title="音频处理与语音识别 API",
    description="提供音频下载、上传和语音识别功能的 API 服务",
    version="1.0.0"
)

# 定义请求模型
class DownloadRequest(BaseModel):
    url: HttpUrl = Field(..., description="要下载的音频URL")
    output_dir: Optional[str] = Field(None, description="输出目录路径")
    verbose: bool = Field(False, description="是否返回详细信息")

class UploadRequest(BaseModel):
    file_path: str = Field(..., description="要上传的本地文件路径")
    custom_filename: Optional[str] = Field(None, description="自定义上传后的文件名")
    link_expires: int = Field(3600, description="下载链接的有效期(秒)")
    access_key: Optional[str] = Field(None, description="七牛云 Access Key")
    secret_key: Optional[str] = Field(None, description="七牛云 Secret Key")
    bucket_name: Optional[str] = Field(None, description="存储空间名称")
    bucket_domain: Optional[str] = Field(None, description="存储空间域名")

class RecognizeRequest(BaseModel):
    file_url: HttpUrl = Field(..., description="音频文件URL（必须是可公网访问的URL）")
    language: str = Field("auto", description="语言代码，默认为auto自动检测")
    keep_tags: bool = Field(False, description="是否保留情感和音频事件标记")
    api_key: Optional[str] = Field(None, description="阿里云 API 密钥")
    verbose: bool = Field(False, description="是否返回详细信息")

class ProcessRequest(BaseModel):
    url: HttpUrl = Field(..., description="要处理的音频URL")
    output_dir: Optional[str] = Field(None, description="音频下载的临时目录")
    language: str = Field("auto", description="语音识别的语言代码，默认为auto自动检测")
    keep_tags: bool = Field(False, description="是否保留情感和音频事件标记")
    link_expires: int = Field(3600, description="七牛云下载链接的有效期(秒)")
    verbose: bool = Field(False, description="是否返回详细信息")
    cleanup: bool = Field(True, description="处理完成后是否清理临时文件和云端文件")
    qiniu_access_key: Optional[str] = Field(None, description="七牛云 Access Key")
    qiniu_secret_key: Optional[str] = Field(None, description="七牛云 Secret Key")
    qiniu_bucket_name: Optional[str] = Field(None, description="存储空间名称")
    qiniu_bucket_domain: Optional[str] = Field(None, description="存储空间域名")
    aliyun_api_key: Optional[str] = Field(None, description="阿里云 API 密钥")

# API 路由
@app.get("/")
async def root():
    """API服务根路径，返回基本信息"""
    return {
        "service": "音频处理与语音识别 API",
        "status": "运行中",
        "endpoints": [
            {"path": "/download", "method": "POST", "description": "下载音频文件"},
            {"path": "/upload", "method": "POST", "description": "上传文件到七牛云"},
            {"path": "/recognize", "method": "POST", "description": "识别音频文件内容"},
            {"path": "/process", "method": "POST", "description": "执行完整工作流"},
            {"path": "/text", "method": "GET", "description": "单纯输出文本结果"}
        ]
    }

@app.post("/download")
async def api_download(request: DownloadRequest):
    """下载音频文件"""
    success, output_file = download_audio(
        url=str(request.url),
        output_dir=request.output_dir,
        verbose=request.verbose
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="下载音频失败")
    
    return {
        "success": success,
        "file_path": output_file
    }

@app.post("/upload")
async def api_upload(request: UploadRequest):
    """上传文件到七牛云"""
    # 获取七牛云配置
    access_key = request.access_key
    secret_key = request.secret_key
    bucket_name = request.bucket_name
    bucket_domain = request.bucket_domain
    
    # 如果未提供 API 密钥，尝试从配置文件获取
    if not all([access_key, secret_key, bucket_name, bucket_domain]):
        try:
            import config
            access_key = access_key or config.QINIU_ACCESS_KEY
            secret_key = secret_key or config.QINIU_SECRET_KEY
            bucket_name = bucket_name or config.QINIU_BUCKET_NAME
            bucket_domain = bucket_domain or config.QINIU_BUCKET_DOMAIN
        except (ImportError, AttributeError):
            raise HTTPException(
                status_code=400, 
                detail="未提供七牛云配置，且无法从配置文件获取"
            )
    
    # 检查文件是否存在
    if not os.path.exists(request.file_path):
        raise HTTPException(status_code=404, detail=f"文件不存在: {request.file_path}")
    
    # 创建上传器并上传文件
    uploader = QiniuUploader(access_key, secret_key, bucket_name, bucket_domain)
    success, result = uploader.upload_file(
        file_path=request.file_path,
        custom_filename=request.custom_filename,
        link_expires=request.link_expires
    )
    
    if not success:
        raise HTTPException(status_code=500, detail=f"上传失败: {result}")
    
    return result

@app.post("/recognize")
async def api_recognize(request: RecognizeRequest):
    """识别音频文件内容"""
    # 初始化语音识别工具
    recognizer = AliyunSpeechRecognition(
        api_key=request.api_key,
        remove_tags=not request.keep_tags
    )
    
    # 执行语音识别
    result = recognizer.recognize_file(
        file_url=str(request.file_url),
        language=request.language,
        verbose=request.verbose
    )
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=f"语音识别失败: {result['error']}")
    
    return result

@app.post("/process")
async def api_process(request: ProcessRequest, background_tasks: BackgroundTasks):
    """执行完整工作流：下载 -> 上传 -> 识别 -> 清理"""
    # 如果提供了API密钥，覆盖环境变量
    if request.qiniu_access_key:
        os.environ["QINIU_ACCESS_KEY"] = request.qiniu_access_key
    if request.qiniu_secret_key:
        os.environ["QINIU_SECRET_KEY"] = request.qiniu_secret_key
    if request.qiniu_bucket_name:
        os.environ["QINIU_BUCKET_NAME"] = request.qiniu_bucket_name
    if request.qiniu_bucket_domain:
        os.environ["QINIU_BUCKET_DOMAIN"] = request.qiniu_bucket_domain
    if request.aliyun_api_key:
        os.environ["DASHSCOPE_API_KEY"] = request.aliyun_api_key
    
    # 执行工作流
    result = process_audio(
        url=str(request.url),
        output_dir=request.output_dir,
        language=request.language,
        keep_tags=request.keep_tags,
        link_expires=request.link_expires,
        verbose=request.verbose,
        save_json=None,  # API模式不保存JSON文件
        cleanup=request.cleanup
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=500, 
            detail={
                "error": result["error"],
                "steps_completed": result["steps_completed"]
            }
        )
    
    return result

@app.get("/text")
async def api_text(
    url: str = Query(..., description="要处理的音频URL"),
    language: str = Query("auto", description="语音识别的语言代码"),
    keep_tags: bool = Query(False, description="是否保留情感和音频事件标记")
):
    """执行完整工作流并只返回纯文本结果"""
    result = process_audio(
        url=url,
        language=language,
        keep_tags=keep_tags,
        cleanup=True,  # 默认清理临时文件
        verbose=False  # 不显示详细信息
    )
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    
    # 返回纯文本结果
    return PlainTextResponse(result["text"])

if __name__ == "__main__":
    # 如果直接运行此脚本，启动 API 服务器
    host = os.environ.get("API_HOST", "0.0.0.0")
    port = int(os.environ.get("API_PORT", 8000))
    
    print(f"🚀 启动 API 服务器 - http://{host}:{port}")
    uvicorn.run("api:app", host=host, port=port, reload=True) 