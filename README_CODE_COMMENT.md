# 代码注释生成功能使用说明

## 功能概述

在 `websocket_simulator2.0.py` 中新增了代码注释生成功能，支持以下特性：

- **双模式运行**: 支持代码补全和代码注释生成两种模式
- **自动读取源文件**: 从指定目录自动加载代码文件
- **多语言支持**: 支持 TypeScript, JavaScript, Python, Java, Go, C/C++ 等多种编程语言
- **批量处理**: 支持批量账号、批量文件处理（单次最多20个文件）

## 新增功能说明

### 1. 运行模式选择

在半自动模式、手动模式和批量模式中，都可以选择运行模式：

```
请选择运行模式:
  1. 代码补全 (Code Completion)
  2. 代码注释生成 (Code Comment Generation)
请输入选项 (1-2, 默认 1):
```

### 2. 源文件目录配置

选择代码注释生成模式后，可以指定源文件目录（默认为 `src`）：

```
请输入源文件目录路径 (默认: src):
```

### 3. 支持的文件类型

- TypeScript: `.ts`, `.tsx`
- JavaScript: `.js`, `.jsx`
- Python: `.py`
- Java: `.java`
- Go: `.go`
- C/C++: `.cpp`, `.c`, `.h`

## 使用示例

### 示例 1: 半自动模式 + 代码注释生成

```bash
python3 websocket_simulator2.0.py
```

1. 选择 `1` (半自动模式)
2. 在浏览器中登录
3. 等待凭证自动提取
4. 选择 `2` (代码注释生成)
5. 输入源文件目录 (例如: `src`)
6. 输入最大任务次数 (例如: `20`)
7. 开始运行

### 示例 2: 手动模式 + 代码注释生成

```bash
python3 websocket_simulator2.0.py
```

1. 选择 `2` (手动模式)
2. 输入 Invoker ID 和 Session ID
3. 选择 `2` (代码注释生成)
4. 输入源文件目录
5. 输入最大任务次数
6. 开始运行

### 示例 3: 批量模式 + 代码注释生成

```bash
python3 websocket_simulator2.0.py
```

1. 选择 `3` (批量模式)
2. 输入配置文件路径 (例如: `accounts.txt`)
3. 选择 `2` (代码注释生成)
4. 输入源文件目录
5. 输入每个账号的最大任务次数
6. 确认并开始批量运行

## WebSocket 通信协议

### 代码注释生成请求格式

```json
{
  "messageName": "CodeChatRequest",
  "context": {
    "messageName": "CodeChatRequest",
    "reqId": "uuid",
    "invokerId": "186812",
    "sessionId": "uuid",
    "version": "2.1.0",
    "apiKey": "api-key"
  },
  "payload": {
    "clientType": "vscode",
    "clientVersion": "1.106.0-insider",
    "gitUrls": [],
    "clientPlatform": "macos-arm64",
    "pluginVersion": "2.1.0",
    "messages": {
      "max_new_tokens": 4096,
      "sub_service": "codecomment",
      "prompts": [
        {
          "role": "system",
          "content": "系统提示词..."
        },
        {
          "files": [
            {
              "path": "/path/to/file.ts",
              "text": "```typescript\n代码内容\n```",
              "startLine": 0,
              "endLine": 100
            }
          ],
          "content": "```typescript\n代码内容\n```\n生成代码注释",
          "role": "user",
          "workItems": []
        }
      ],
      "dialogId": "uuid",
      "questionType": "newAsk",
      "parentReqId": "",
      "kbId": ""
    }
  }
}
```

### 代码注释生成响应格式

响应是流式的，会收到多个 `CodeChatRequest_resp` 消息：

```json
{
  "messageName": "CodeChatRequest_resp",
  "context": {
    "optResult": 0,
    "reqId": "uuid"
  },
  "payload": {
    "messageName": "CodeChatResponse",
    "invokerId": "186812",
    "reqId": "uuid",
    "seqId": 0,
    "retCode": 0,
    "isEnd": 0,  // 0表示未结束，1表示结束
    "answer": "注释内容片段",
    "inValid": false
  }
}
```

## 关键差异对比

| 特性 | 代码补全 | 代码注释生成 |
|------|----------|--------------|
| MessageName | CodeGenRequest | CodeChatRequest |
| Sub Service | - | codecomment |
| 输入方式 | prefix + suffix | 完整文件内容 |
| Max Tokens | 256 | 4096 |
| 响应方式 | 单次 | 流式 (isEnd标记) |
| Version | 2.0.0 | 2.1.0 |

## 注意事项

1. **文件数量限制**: 单次最多处理20个源文件（自动随机选择）
2. **文件编码**: 文件必须是 UTF-8 编码
3. **空文件跳过**: 自动跳过空文件或读取失败的文件
4. **随机选择**: 每次请求随机选择一个文件进行注释生成
5. **流式输出**: 代码注释生成采用流式输出，需等待 `isEnd=1` 才算完成

## 代码结构

### 新增方法

```python
class CodeFreeSimulator:
    def _load_src_files(self)                    # 加载源文件列表
    def _read_file_content(self, filepath: str)  # 读取文件内容
    def _get_file_language(self, filepath: str)  # 判断文件语言
    async def request_code_comment(self)          # 请求代码注释生成
```

### 修改方法

```python
class CodeFreeSimulator:
    def __init__(self, ..., mode: str, src_dir: str)  # 新增mode和src_dir参数
    async def start_coding_simulation(self)           # 根据mode选择不同请求
    async def handle_message(self, data: str)         # 新增CodeChatRequest_resp处理
```

## 故障排除

### 问题 1: 找不到源文件
**解决方案**: 确保 `src` 目录存在且包含代码文件

### 问题 2: 文件读取失败
**解决方案**: 检查文件编码是否为 UTF-8

### 问题 3: 没有响应
**解决方案**: 检查 API 密钥是否有效，凭证是否过期

## 更新日志

### v2.0 -> v2.1
- ✅ 新增代码注释生成模式
- ✅ 支持多种编程语言文件自动识别
- ✅ 支持从指定目录批量加载源文件
- ✅ 优化用户交互界面，支持模式选择
- ✅ 新增流式响应处理逻辑
