#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
阿里云语音识别工具
使用DashScope SDK调用SenseVoice录音语音识别服务
"""

import os
import sys
import json
import argparse
import requests
import re
from http import HTTPStatus
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 导入DashScope SDK
try:
    import dashscope
    from dashscope.audio.asr import Transcription
except ImportError:
    print("❌ 错误: 未安装DashScope SDK")
    print("请通过以下命令安装: pip install dashscope")
    sys.exit(1)

class AliyunSpeechRecognition:
    """阿里云语音识别工具类"""
    
    def __init__(self, api_key: Optional[str] = None, remove_tags: bool = True):
        """
        初始化语音识别工具
        
        参数:
            api_key: 阿里云API密钥，不提供则从环境变量获取
            remove_tags: 是否移除情感和音频事件标记，默认为True
        """
        # 获取API密钥(优先级：参数 > 环境变量)
        self.api_key = api_key or os.environ.get("DASHSCOPE_API_KEY")
            
        if not self.api_key:
            raise ValueError("缺少阿里云API密钥，请在参数中提供或设置DASHSCOPE_API_KEY环境变量")
        
        # 设置API密钥
        dashscope.api_key = self.api_key
        
        # 是否移除标记
        self.remove_tags = remove_tags
    
    def recognize_file(self, file_url: str, language: str = 'auto', verbose: bool = False) -> Dict[str, Any]:
        """
        识别音频文件内容
        
        参数:
            file_url: 音频文件URL（必须是可公网访问的URL）
            language: 语言代码，默认为auto自动检测
            verbose: 是否显示详细日志
            
        返回:
            识别结果字典
        """
        if verbose:
            print(f"🔍 开始识别音频: {file_url}")
            print(f"🌐 识别语言设置: {language}")
        
        # 提交异步识别任务
        try:
            # 构建语言提示列表
            language_hints = [language]
            
            # 调用异步API提交任务
            task_response = Transcription.async_call(
                model='sensevoice-v1',
                file_urls=[file_url],
                language_hints=language_hints
            )
            
            if verbose:
                print(f"✅ 任务提交成功，任务ID: {task_response.output.task_id}")
                print(f"⏳ 任务状态: {task_response.output.task_status}")
                print("⏳ 正在等待任务完成...")
            
            # 同步等待任务完成
            transcribe_response = Transcription.wait(task=task_response.output.task_id)
            
            if transcribe_response.status_code == HTTPStatus.OK:
                if verbose:
                    print(f"✅ 任务完成，状态: {transcribe_response.output.task_status}")
                
                # 返回任务结果
                return self._process_transcription_result(transcribe_response.output, verbose)
            else:
                print(f"❌ 错误: API返回错误状态码 {transcribe_response.status_code}")
                return {"error": f"API返回错误状态码: {transcribe_response.status_code}"}
                
        except Exception as e:
            print(f"❌ 识别失败: {str(e)}")
            return {"error": str(e)}
    
    def _clean_text(self, text: str) -> str:
        """
        清理文本，移除情感和音频事件标记
        
        参数:
            text: 原始识别文本
            
        返回:
            清理后的文本
        """
        # 如果不需要移除标记，直接返回原始文本
        if not self.remove_tags:
            return text
        
        # 移除所有尖括号及其内容 <...>
        text = re.sub(r'<[^>]*>', '', text)
        
        # 移除情感标记 (|HAPPY|, |SAD|, |ANGRY|, |NEUTRAL| 等)
        text = re.sub(r'\|[A-Z]+\|', '', text)
        
        # 移除音频事件标记 (|Applause|...|/Applause| 等)
        # 先移除事件结束标记
        text = re.sub(r'\|/[A-Za-z]+\|', '', text)
        # 再移除事件开始标记
        text = re.sub(r'\|[A-Za-z]+\|', '', text)
        
        # 移除多余空格
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    
    def _process_transcription_result(self, output, verbose: bool = False) -> Dict[str, Any]:
        """处理转录结果"""
        result = {}
        
        if output.task_status != "SUCCEEDED":
            if verbose:
                print(f"⚠️ 任务未成功完成，状态: {output.task_status}")
            return {"error": f"任务状态: {output.task_status}"}
        
        # 检查是否有结果
        if not hasattr(output, 'results') or not output.results:
            return {"error": "没有识别结果"}
        
        # 处理每个子任务的结果
        all_texts = []
        clean_texts = []
        for idx, item in enumerate(output.results):
            if item.get('subtask_status') != "SUCCEEDED":
                if verbose:
                    print(f"⚠️ 子任务 {idx+1} 失败: {item.get('message', '未知错误')}")
                continue
            
            # 获取识别结果URL
            transcription_url = item.get('transcription_url')
            if not transcription_url:
                continue
                
            try:
                # 下载识别结果
                if verbose:
                    print(f"📥 下载识别结果: {transcription_url}")
                    
                response = requests.get(transcription_url)
                response.raise_for_status()
                
                # 解析JSON结果
                transcript_data = response.json()
                
                # 提取文本内容
                if 'transcripts' in transcript_data and transcript_data['transcripts']:
                    for transcript in transcript_data['transcripts']:
                        if 'text' in transcript:
                            # 保存原始文本
                            original_text = transcript['text']
                            all_texts.append(original_text)
                            
                            # 清理文本并保存
                            clean_text = self._clean_text(original_text)
                            clean_texts.append(clean_text)
                
                # 保存详细结果
                if idx == 0:  # 只保存第一个文件的详细信息
                    result['details'] = transcript_data
                
            except Exception as e:
                if verbose:
                    print(f"❌ 下载或解析识别结果失败: {str(e)}")
        
        # 合并所有文本
        result['original_text'] = "\n".join(all_texts)
        result['text'] = "\n".join(clean_texts)
        
        return result

def process_recognition_result(result_json, keep_tags=False):
    """
    处理识别结果，根据需要去除标记
    
    参数:
        result_json: API返回的JSON结果
        keep_tags: 是否保留情感和音频事件标记
        
    返回:
        处理后的文本和原始文本
    """
    # 获取原始文本
    original_text = result_json.get('text', '')
    
    # 如果需要保留标记，直接返回原始文本
    if keep_tags:
        return original_text, original_text
    
    # 否则处理文本，去除所有标记
    processed_text = original_text
    # 移除所有尖括号及其内容
    processed_text = re.sub(r'<[^>]*>', '', processed_text)
    # 去除其他类型的标记
    processed_text = re.sub(r'\[.*?\]', '', processed_text)
    processed_text = re.sub(r'\|[A-Z]+\|', '', processed_text)
    processed_text = re.sub(r'\|/[A-Za-z]+\|', '', processed_text)
    processed_text = re.sub(r'\|[A-Za-z]+\|', '', processed_text)
    
    return processed_text, original_text

def main():
    """主函数，处理命令行参数并执行语音识别"""
    # 创建参数解析器
    parser = argparse.ArgumentParser(description="阿里云语音识别工具")
    parser.add_argument("url", help="音频文件URL（必须是可公网访问的URL）")
    parser.add_argument("-k", "--api-key", help="阿里云API密钥")
    parser.add_argument("-l", "--language", default="auto", help="语言代码，默认为auto自动检测")
    parser.add_argument("-v", "--verbose", action="store_true", help="显示详细信息")
    parser.add_argument("-o", "--output", help="保存识别结果的JSON文件路径")
    parser.add_argument("--keep-tags", action="store_true", help="保留情感和音频事件标记")
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 初始化语音识别工具
    recognizer = AliyunSpeechRecognition(
        api_key=args.api_key,
        remove_tags=not args.keep_tags
    )
    
    # 执行语音识别
    result = recognizer.recognize_file(
        file_url=args.url,
        language=args.language,
        verbose=args.verbose
    )
    
    # 处理结果
    if "error" in result:
        print(f"❌ 识别失败: {result['error']}")
        sys.exit(1)
    
    # 显示识别文本
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
    
    # 保存结果到文件
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"✅ 完整结果已保存至: {args.output}")
        except Exception as e:
            print(f"❌ 保存结果失败: {str(e)}")
    
if __name__ == "__main__":
    main() 