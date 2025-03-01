# 音频处理与语音识别工具集

这个工具集提供了一套完整的音频处理解决方案，包括音频下载、云存储上传和语音识别功能。主要组件包括：

- 音频下载工具 (基于yt-dlp)
- 七牛云文件上传与链接生成工具
- 阿里云语音识别工具 (基于DashScope API)
- 一体化工作流处理工具

## 目录

- [安装](#安装)
- [配置](#配置)
- [音频下载](#音频下载)
- [云存储上传](#云存储上传)
- [语音识别](#语音识别)
- [一体化工作流](#一体化工作流)
- [完整工作流示例](#完整工作流示例)
- [常见问题](#常见问题)
- [API 服务](#api-服务)

## 安装

### 1. 克隆项目
```bash
git clone <项目仓库地址>
cd <项目目录>
```
### 2. 安装依赖

使用pip安装所需的依赖包：

```bash
pip install -r requirements.txt
```

## 配置

所有API密钥和服务配置统一保存在`config.py`文件中。

### 七牛云配置

在`config.py`中填写七牛云账号信息：
```python
# 七牛云配置
QINIU_ACCESS_KEY = "您的七牛云Access Key"
QINIU_SECRET_KEY = "您的七牛云Secret Key"
QINIU_BUCKET_NAME = "您的存储空间名称"
QINIU_BUCKET_DOMAIN = "您的存储空间域名"
```

### 阿里云配置

在`config.py`中填写阿里云DashScope API密钥：
```python
# 阿里云配置
ALIYUN_API_KEY = "您的阿里云DashScope API密钥"
```

## 音频下载

`download_audio.py` 支持从各种网站下载音频文件。

### 基本用法
```bash
python download_audio.py <URL>
```

### 高级选项
```bash
# 指定输出目录
python download_audio.py <URL> -o /path/to/output

# 显示详细下载信息
python download_audio.py <URL> -v
```

### 参数说明

| 参数 | 说明 |
|------|------|
| `url` | 要下载的音频URL (必须) |
| `-o, --output-dir` | 指定输出目录 (可选，默认为当前目录下的downloads_temp) |
| `-v, --verbose` | 显示详细下载信息 (可选) |

## 云存储上传

`qiniu_upload.py` 用于将文件上传至七牛云存储并生成带签名的下载链接。

### 基本用法
```bash
python qiniu_upload.py <本地文件路径>
```

### 高级选项
```bash
# 指定远程文件名
python qiniu_upload.py <本地文件路径> <远程文件名>

# 指定链接有效期(单位:秒，默认3600秒)
python qiniu_upload.py <本地文件路径> <远程文件名> 86400
```

### 参数说明

| 参数 | 说明 |
|------|------|
| `<本地文件路径>` | 要上传的本地文件路径 (必须) |
| `<远程文件名>` | 存储在云端的文件名 (可选) |
| `<链接有效期>` | 生成的下载链接有效期，单位为秒 (可选，默认3600秒) |

## 语音识别

`aliyun_speech_recognition.py` 使用阿里云DashScope API对音频文件进行语音识别。

### 基本用法
```bash
python aliyun_speech_recognition.py <音频文件URL>
```

### 高级选项
```bash
# 指定语言(例如中文)
python aliyun_speech_recognition.py <音频文件URL> -l zh

# 保留情感和音频事件标记
python aliyun_speech_recognition.py <音频文件URL> --keep-tags

# 保存完整识别结果到JSON文件
python aliyun_speech_recognition.py <音频文件URL> -o result.json

# 显示详细处理信息
python aliyun_speech_recognition.py <音频文件URL> -v
```

### 参数说明

| 参数 | 说明 |
|------|------|
| `url` | 音频文件URL (必须是可公网访问的链接) |
| `-k, --api-key` | 阿里云API密钥 (可选，优先使用配置文件) |
| `-l, --language` | 语言代码，如zh、en等 (可选，默认auto自动检测) |
| `-v, --verbose` | 显示详细处理信息 (可选) |
| `-o, --output` | 保存结果的JSON文件路径 (可选) |
| `--keep-tags` | 保留情感和音频事件标记 (可选，默认去除) |

## 一体化工作流

`main.py` 集成了下载、上传和识别三个步骤，提供一站式处理方案。

### 基本用法
```bash
python main.py <URL>
```

### 高级选项
```bash
# 指定语言为中文并显示详细处理信息
python main.py <URL> -l zh -v

# 保留情感和音频事件标记
python main.py <URL> --keep-tags

# 自定义七牛云链接有效期为24小时并保存识别结果
python main.py <URL> -e 86400 -s result.json

# 处理完成后自动清理临时文件和云端文件
python main.py <URL> --cleanup

# 组合使用多个选项
python main.py <URL> -l zh -v --cleanup -s result.json
```

### 参数说明

| 参数 | 说明 |
|------|------|
| `url` | 要处理的音频URL (必须) |
| `-o, --output-dir` | 音频下载的临时目录 (可选) |
| `-l, --language` | 语音识别的语言代码 (可选，默认auto) |
| `--keep-tags` | 保留情感和音频事件标记 (可选，默认去除) |
| `-e, --expires` | 七牛云下载链接的有效期，单位秒 (可选，默认3600) |
| `-v, --verbose` | 显示详细处理信息 (可选) |
| `-s, --save` | 保存识别结果的JSON文件路径 (可选) |
| `--cleanup` | 处理完成后自动清理临时文件和云端文件 (可选) |

## 完整工作流示例

下面是几种不同使用场景的示例：

### 基础使用 - 处理YouTube视频
```bash
# 使用一体化工具
python main.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" -l en

# 或者分步骤执行
python download_audio.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
python qiniu_upload.py "downloads_temp/video_title.aac"
python aliyun_speech_recognition.py "<七牛云URL>" -l en
```

### 处理中文播客
```bash
python main.py "https://example.com/podcast.mp3" -l zh -v -s result.json
```

### 分析情感内容
```bash
python main.py "https://example.com/interview.mp3" --keep-tags -l en
```

## 常见问题

### 1. 上传到七牛云后无法访问文件

确保您的七牛云存储空间设置正确。此工具生成的是带签名的私有链接，有效期默认为1小时。如需更长时间，请使用`-e`参数指定有效期（单位：秒）。

### 2. 语音识别结果不准确

尝试使用`-l`参数指定正确的语言。例如，对于中文音频，使用`-l zh`。某些方言或背景噪音较大的音频可能会影响识别准确率。

### 3. 下载音频失败

确保已安装最新版的yt-dlp，并且URL有效。某些网站可能限制下载，请确保您有权访问该内容。可以尝试添加`-v`参数查看详细错误信息。

### 4. API密钥无效

确保在`config.py`中正确填写了七牛云和阿里云的API密钥。您也可以通过命令行参数直接指定API密钥。

### 5. 文件过大处理失败

阿里云语音识别API对文件大小有限制（通常为2GB以内）。对于大型文件，可能需要先分割后再处理。

## API 服务

本工具集同时提供了 API 服务接口，可以通过 HTTP 请求使用所有功能。

### 启动 API 服务

```bash
# 直接启动服务
python api.py

# 或者使用 uvicorn 启动（支持热重载）
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### API 文档

服务启动后，可以访问自动生成的 API 文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### API 端点概览

| 端点 | 方法 | 描述 |
|------|------|------|
| `/` | GET | 返回 API 基本信息 |
| `/download` | POST | 下载音频文件 |
| `/upload` | POST | 上传文件到七牛云 |
| `/recognize` | POST | 识别音频文件内容 |
| `/process` | POST | 执行完整工作流 |
| `/text` | GET | 执行工作流并只返回纯文本结果 |

### API 使用示例

#### 示例 1: 基本文本识别

使用 `/text` 端点可以快速获取音频内容的纯文本识别结果：

```bash
curl -X GET "http://localhost:8000/text?url=https://example.com/abcd"
```

#### 示例 2: 带 API 密钥的完整请求

完整的 cURL 示例，包含所有密钥和选项：

```bash
curl -X POST "http://localhost:8000/process" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/abcd",
    "language": "auto",
    "keep_tags": false,
    "link_expires": 7200,
    "verbose": false,
    "cleanup": true,
    "qiniu_access_key": "您的七牛云AccessKey",
    "qiniu_secret_key": "您的七牛云SecretKey",
    "qiniu_bucket_name": "您的存储空间名称",
    "qiniu_bucket_domain": "您的存储空间域名",
    "aliyun_api_key": "您的阿里云API密钥"
  }'
```

#### 示例 3: 仅下载音频

```bash
curl -X POST "http://localhost:8000/download" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "verbose": true
  }'
```

#### 示例 4: 仅执行语音识别

```bash
curl -X POST "http://localhost:8000/recognize" \
  -H "Content-Type: application/json" \
  -d '{
    "file_url": "https://example.com/abcd",
    "language": "en", 
    "api_key": "您的阿里云API密钥",
    "keep_tags": true
  }'
```

### API 返回格式

- `/text` 端点直接返回纯文本
- 其他端点返回 JSON 格式的详细结果

### API 安全注意事项

API 服务默认没有启用认证机制。在生产环境中部署时，建议：

1. 设置反向代理（如 Nginx）并启用 HTTPS
2. 实现适当的认证机制
3. 限制 API 的访问范围

请避免在公共网络上暴露含有密钥参数的 API 调用。