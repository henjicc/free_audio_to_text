#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
音频处理与语音识别 API 服务
使用 FastAPI 提供基于 HTTP 的服务接口
"""

import os
import sys
import json
import logging
import time
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler  # 添加导入
from typing import Optional, Dict, Any
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl, Field

# 配置日志系统 - 使用轮转日志处理器
# 创建日志目录
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "api_server.log")

# 配置轮转日志处理器
file_handler = TimedRotatingFileHandler(
    filename=log_file,
    when="midnight",  # 每天午夜轮转
    interval=1,       # 每1个单位轮转一次
    backupCount=7,    # 保留7个备份文件
    encoding="utf-8"  # 使用UTF-8编码
)
file_handler.suffix = "%Y-%m-%d.log"  # 轮转文件后缀格式

# 配置日志格式
log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(log_format)

# 配置控制台输出
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_format)

# 创建日志记录器
logger = logging.getLogger("audio-api")
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# 确保不重复添加处理器
if logger.hasHandlers():
    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

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

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有源，生产环境应该设置具体的源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = f"{int(time.time())}-{id(request)}"
    
    # 记录请求开始
    logger.info(f"Request [{request_id}] - {request.method} {request.url.path}")
    
    # 记录请求头
    headers_log = {k: v for k, v in request.headers.items() 
                  if k.lower() not in ("authorization", "x-api-key")}  # 排除敏感头信息
    logger.info(f"Request [{request_id}] headers: {headers_log}")
    
    # 尝试记录请求体，但不记录敏感信息
    try:
        body = await request.body()
        if body:
            body_text = body.decode()
            try:
                # 尝试解析为JSON并隐藏敏感字段
                body_json = json.loads(body_text)
                # 隐藏敏感信息
                for key in body_json:
                    if any(sensitive in key.lower() for sensitive in 
                          ["key", "secret", "password", "token", "api_key"]):
                        body_json[key] = "***HIDDEN***"
                logger.info(f"Request [{request_id}] body: {json.dumps(body_json)}")
            except:
                # 如果不是JSON或解析失败，记录长度
                logger.info(f"Request [{request_id}] body length: {len(body_text)} bytes")
    except:
        pass
    
    # 记录处理时间
    start_time = time.time()
    
    # 调用下一个处理器
    response = await call_next(request)
    
    # 计算处理时间并记录
    process_time = time.time() - start_time
    response_status = response.status_code
    
    logger.info(f"Response [{request_id}] - Status: {response_status}, Time: {process_time:.4f}s")
    
    return response

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

# 添加一个新的请求模型用于 /text 端点
class TextRequest(BaseModel):
    url: HttpUrl = Field(..., description="要处理的音频URL")
    language: str = Field("auto", description="语音识别的语言代码，默认为auto自动检测")
    keep_tags: bool = Field(False, description="是否保留情感和音频事件标记")
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
    logger.info("访问了API根路径")
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
    logger.info(f"下载音频请求: {str(request.url)}")
    
    success, output_file = download_audio(
        url=str(request.url),
        output_dir=request.output_dir,
        verbose=True  # 修改为True，始终显示详细信息用于日志
    )
    
    if not success:
        logger.error(f"下载音频失败: {str(request.url)}")
        raise HTTPException(status_code=500, detail="下载音频失败")
    
    logger.info(f"下载音频成功: {output_file}")
    return {
        "success": success,
        "file_path": output_file
    }

@app.post("/upload")
async def api_upload(request: UploadRequest):
    """上传文件到七牛云"""
    logger.info(f"上传文件请求: {request.file_path}")
    
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
        logger.error(f"文件不存在: {request.file_path}")
        raise HTTPException(status_code=404, detail=f"文件不存在: {request.file_path}")
    
    # 创建上传器并上传文件
    try:
        logger.info(f"开始上传文件: {request.file_path} 到七牛云")
        uploader = QiniuUploader(access_key, secret_key, bucket_name, bucket_domain)
        success, result = uploader.upload_file(
            file_path=request.file_path,
            custom_filename=request.custom_filename,
            link_expires=request.link_expires
        )
    
        if not success:
            logger.error(f"上传失败: {result}")
            raise HTTPException(status_code=500, detail=f"上传失败: {result}")
    
        logger.info(f"上传成功: {result.get('filename', '未知文件名')}")
        return result
    except Exception as e:
        logger.exception(f"上传过程发生异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"上传过程发生异常: {str(e)}")

@app.post("/recognize")
async def api_recognize(request: RecognizeRequest):
    """识别音频文件内容"""
    logger.info(f"识别音频请求: {str(request.file_url)}, 语言: {request.language}")
    
    # 初始化语音识别工具
    try:
        recognizer = AliyunSpeechRecognition(
            api_key=request.api_key,
            remove_tags=not request.keep_tags
        )
    
        # 执行语音识别
        logger.info(f"开始识别: {str(request.file_url)}")
        result = recognizer.recognize_file(
            file_url=str(request.file_url),
            language=request.language,
            verbose=True  # 修改为True，始终显示详细信息用于日志
        )
    
        if "error" in result:
            logger.error(f"识别失败: {result['error']}")
            raise HTTPException(status_code=500, detail=f"语音识别失败: {result['error']}")
    
        logger.info(f"识别成功: 文本长度 {len(result.get('text', ''))}")
        return result
    except Exception as e:
        logger.exception(f"识别过程发生异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"识别过程发生异常: {str(e)}")

@app.post("/process")
async def api_process(request: ProcessRequest, background_tasks: BackgroundTasks):
    """执行完整工作流：下载 -> 上传 -> 识别 -> 清理"""
    logger.info(f"处理完整流程请求: {str(request.url)}, 语言: {request.language}")
    
    # 如果提供了API密钥，覆盖环境变量 (隐去实际值不记录)
    if request.qiniu_access_key:
        logger.info("使用请求提供的七牛云 Access Key")
        os.environ["QINIU_ACCESS_KEY"] = request.qiniu_access_key
    if request.qiniu_secret_key:
        logger.info("使用请求提供的七牛云 Secret Key")
        os.environ["QINIU_SECRET_KEY"] = request.qiniu_secret_key
    if request.qiniu_bucket_name:
        logger.info(f"使用请求提供的七牛云 Bucket: {request.qiniu_bucket_name}")
        os.environ["QINIU_BUCKET_NAME"] = request.qiniu_bucket_name
    if request.qiniu_bucket_domain:
        logger.info(f"使用请求提供的七牛云域名: {request.qiniu_bucket_domain}")
        os.environ["QINIU_BUCKET_DOMAIN"] = request.qiniu_bucket_domain
    if request.aliyun_api_key:
        logger.info("使用请求提供的阿里云 API Key")
        os.environ["DASHSCOPE_API_KEY"] = request.aliyun_api_key
    
    # 执行工作流
    try:
        logger.info("开始执行完整工作流")
        result = process_audio(
            url=str(request.url),
            output_dir=request.output_dir,
            language=request.language,
            keep_tags=request.keep_tags,
            link_expires=request.link_expires,
            verbose=True,  # 修改为True，始终显示详细信息用于日志
            save_json=None,  # API模式不保存JSON文件
            cleanup=request.cleanup
        )
    
        if not result["success"]:
            logger.error(f"处理失败: {result['error']}")
            logger.info(f"已完成步骤: {', '.join(result['steps_completed'])}")
            raise HTTPException(
                status_code=500, 
                detail={
                    "error": result["error"],
                    "steps_completed": result["steps_completed"]
                }
            )
    
        logger.info(f"处理成功! 完成步骤: {', '.join(result['steps_completed'])}")
        return result
    except Exception as e:
        logger.exception(f"处理过程发生异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理过程发生异常: {str(e)}")

@app.get("/text")
async def api_text_get(
    url: str = Query(..., description="要处理的音频URL"),
    language: str = Query("auto", description="语音识别的语言代码"),
    keep_tags: bool = Query(False, description="是否保留情感和音频事件标记")
):
    """执行完整工作流并只返回纯文本结果 (GET 方法)"""
    logger.info(f"文本识别请求(GET): {url}, 语言: {language}")
    
    try:
        logger.info("开始执行文本识别工作流")
        result = process_audio(
            url=url,
            language=language,
            keep_tags=keep_tags,
            cleanup=True,  # 默认清理临时文件
            verbose=True  # 修改为True，始终显示详细信息用于日志
        )
    
        if not result["success"]:
            logger.error(f"文本识别失败: {result['error']}")
            raise HTTPException(status_code=500, detail=result["error"])
    
        logger.info(f"文本识别成功: 文本长度 {len(result['text'])}")
        # 返回纯文本结果
        return PlainTextResponse(result["text"])
    except Exception as e:
        logger.exception(f"文本识别过程发生异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文本识别过程发生异常: {str(e)}")

# 添加新的 POST 端点，支持传入 API 密钥
@app.post("/text")
async def api_text_post(request: TextRequest):
    """执行完整工作流并只返回纯文本结果 (POST 方法，支持传入 API 密钥)"""
    logger.info(f"文本识别请求(POST): {str(request.url)}, 语言: {request.language}")
    
    # 如果提供了API密钥，覆盖环境变量
    if request.qiniu_access_key:
        logger.info("使用请求提供的七牛云 Access Key")
        os.environ["QINIU_ACCESS_KEY"] = request.qiniu_access_key
    if request.qiniu_secret_key:
        logger.info("使用请求提供的七牛云 Secret Key")
        os.environ["QINIU_SECRET_KEY"] = request.qiniu_secret_key
    if request.qiniu_bucket_name:
        logger.info(f"使用请求提供的七牛云 Bucket: {request.qiniu_bucket_name}")
        os.environ["QINIU_BUCKET_NAME"] = request.qiniu_bucket_name
    if request.qiniu_bucket_domain:
        logger.info(f"使用请求提供的七牛云域名: {request.qiniu_bucket_domain}")
        os.environ["QINIU_BUCKET_DOMAIN"] = request.qiniu_bucket_domain
    if request.aliyun_api_key:
        logger.info("使用请求提供的阿里云 API Key")
        os.environ["DASHSCOPE_API_KEY"] = request.aliyun_api_key
    
    try:
        logger.info("开始执行文本识别工作流")
        result = process_audio(
            url=str(request.url),
            language=request.language,
            keep_tags=request.keep_tags,
            cleanup=request.cleanup,
            verbose=True  # 修改为True，始终显示详细信息用于日志
        )
    
        if not result["success"]:
            logger.error(f"文本识别失败: {result['error']}")
            raise HTTPException(status_code=500, detail=result["error"])
    
        logger.info(f"文本识别成功: 文本长度 {len(result['text'])}")
        # 返回纯文本结果
        return PlainTextResponse(result["text"])
    except Exception as e:
        logger.exception(f"文本识别过程发生异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文本识别过程发生异常: {str(e)}")

if __name__ == "__main__":
    # 如果直接运行此脚本，启动 API 服务器
    host = os.environ.get("API_HOST", "0.0.0.0")
    port = int(os.environ.get("API_PORT", 8000))
    
    logger.info(f"🚀 启动 API 服务器 - http://{host}:{port}")
    print(f"🚀 启动 API 服务器 - http://{host}:{port}")
    
    # 记录启动日志
    logger.info("=" * 50)
    logger.info(f"API服务启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"主机: {host}, 端口: {port}")
    logger.info("=" * 50)
    
    uvicorn.run("api:app", host=host, port=port, reload=True) 