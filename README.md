# 下载网页音频并转为文本

基本可以免费用，主要用到了以下几个工具：

- yt-dlp：下载音频
- 七牛云：文件上传与链接生成工具
- SenseVoice API：将音频转为文本


## 部署
### 本地部署

1. 克隆项目
```bash
git clone https://github.com/henjicc/free_audio_to_text.git
cd free_audio_to_text
```
2. 安装依赖
使用pip安装所需的依赖包：

```bash
pip install -r requirements.txt
```
### Docker部署

#### 复制配置文件并填写必要信息
```bash
cp .env.example .env
# 编辑.env文件，填写密钥信息，设置端口
```

#### 构建并启动容器
```bash
docker-compose up -d
```

#### 重新构建
如果修改了代码或Dockerfile，需要重新构建镜像：

```bash
docker-compose build
docker-compose up -d
```
## 配置

1. 复制 `.env.example` 文件为 `.env`
2. 编辑 `.env` 文件，填写相关配置信息


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

## 一键搞定

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
| `/text` | GET | 执行工作流并只返回纯文本结果 |
| `/download` | POST | 下载音频文件 |
| `/upload` | POST | 上传文件到七牛云 |
| `/recognize` | POST | 识别音频文件内容 |
| `/process` | POST | 执行完整工作流 |

### API 使用示例

#### 示例 1: 基本文本识别

使用 `/text` 端点可以快速获取音频内容的纯文本识别结果：

```bash
curl -X GET "http://localhost:8000/text?url=https://example.com/abcd"
```

#### 示例 2: 一键搞定，同时设置参数


```bash
curl -X POST "http://localhost:8000/process" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/abcd",
    "language": "auto",
    "keep_tags": false,
    "link_expires": 7200,
    "verbose": false,
    "cleanup": true
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
    "language": "auto", 
    "keep_tags": true
  }'
```

### API 返回格式

- `/text` 端点直接返回纯文本
- 其他端点返回 JSON 格式的详细结果