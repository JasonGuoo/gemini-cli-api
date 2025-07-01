# Gemini CLI API

该项目通过包装 `gemini-cli` 工具，提供了一个**与 OpenAI API 规范兼容的 RESTful API**。这使得开发人员能够利用谷歌强大的 Gemini 模型，并使用现有的、与 OpenAI 兼容的应用程序和库，而只需极少甚至无需更改代码。

### 免费套餐的优势：Gemini CLI vs. Gemini API

该项目的一个关键区别在于它能够利用 Google AI Studio 提供的**慷慨的免费套餐**（`gemini-cli` 通过它访问）。这为开发和原型设计提供了显著优势：

| 功能 | Gemini CLI (通过 Google AI Studio 免费套餐) | 直接 Gemini API (付费套餐) |
| :-------------------------- | :------------------------------------------ | :---------------------------- |
| **成本** | 免费 | 按使用量付费 |
| **每用户每分钟请求数** | 120 | 更贵 |
| **每用户每天请求数** | 1000 (个人), 1500 (标准) | 更贵 |

这意味着您可以开发和广泛测试您的 AI 驱动的应用程序而无需支付 API 费用，使其成为以下场景的理想解决方案：

-   **零成本开发：** 无需花费 API 调用费用即可构建和测试利用 Gemini 模型的应用程序。
-   **即时兼容性：** 只需更改 API 基础 URL，即可与庞大的 OpenAI 兼容工具和库生态系统无缝集成。

### 主要功能
-   **OpenAI API 兼容性：** 提供一个模拟 OpenAI 标准的 `/v1/chat/completions` 端点。
-   **无状态交互：** 每个 API 调用都会调用一个新的 `gemini --prompt` 进程，确保每个请求都以完全无状态的方式处理。
-   **流式支持：** 为交互式应用程序支持实时流式响应，并针对多语言内容进行了优化。
## 先决条件

在运行此服务器之前，您必须已安装 `gemini-cli` 工具，并且其可执行命令 `gemini` 必须在您系统的 `PATH` 中可用。您可以在[此处](https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/cli)找到安装说明。

## 快速入门

要启动 API 服务器，只需运行提供的 shell 脚本：

```bash
./start_server.sh
```

此脚本将：
1.  从您的 `.env` 文件加载环境变量（如果存在）。
2.  执行快速检查以确保 `gemini` CLI 可访问。
3.  使用 `uvicorn` 启动 FastAPI 应用程序。

服务器通常会运行在 `http://localhost:8000`（或您在 `.env` 文件中指定的端口）。然后，您可以在 `http://localhost:8000/docs` 访问 API 文档。

### 快速入门示例

服务器运行后，您可以使用 `curl` 发出请求：

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{ "model": "gemini-2.5-flash", "messages": [{"role": "user", "content": "你好，今天过得怎么样？"}], "stream": false }'
```

## 局限性

使用 `gemini-cli` 作为 API 服务器的后端会带来一些用户需要注意的重要局限性：

1.  **忽略的 API 参数：** `gemini-cli` 工具不支持官方 OpenAI 聊天补全 API 中的所有参数。因此，像 `temperature`、`top_p`、`n`、`stop`、`max_tokens`、`presence_penalty`、`frequency_penalty` 和 `logit_bias` 等参数将被**接受但被忽略**。

2.  **模型选择：** API 请求（`POST /v1/chat/completions`）中的 `model` 参数用于选择 Gemini 模型。目前，仅明确支持 `gemini-2.5-flash` 和 `gemini-2.5-pro`。如果请求了不支持的模型，服务器将回退到您 `.env` 文件中配置的 `DEFAULT_GEMINI_MODEL`。请注意如果超出免费额度，可能会被Google返回429错误，从而导致整个调用返回500错误。

3.  **Token 使用情况：** 使用 `--prompt` 标志时，`gemini-cli` 不提供 Token 使用信息。因此，API 响应中的 `usage` 字段将始终为 `null`。

4.  **性能：** 每个 API 调用都涉及生成一个新的命令行子进程，与原生 API 集成相比，这会引入额外的开销和延迟。

5.  **错误处理：** 错误直接依赖于 `gemini` 子进程的输出和退出代码，其结构化和详细程度可能不如原生 API 错误。

## 配置

该服务器利用环境变量进行配置，可以通过项目根目录下的 `.env` 文件方便地管理。服务器启动时，它会自动加载这些变量，使它们对 FastAPI 应用程序和底层的 `gemini` CLI 进程都可用。

以下是您可以在 `.env` 文件中设置的一些关键配置选项：

```dotenv
# 您的 Gemini API 密钥 (gemini-cli 运行所必需)
GEMINI_API_KEY=your_api_key_here

# 您的 Google Cloud 项目 ID (如果 gemini-cli 需要)
# GOOGLE_CLOUD_PROJECT=your_project_id

# 服务器端口: FastAPI 服务器将监听的端口。
# 如果未指定，则默认为 8000。
PORT=8000

# 默认 Gemini 模型: 如果客户端未指定支持的模型
# 或指定了无效的模型，则使用此模型。支持的值为 "gemini-2.5-flash" 或 "gemini-2.5-pro"。
# 默认为 "gemini-2.5-flash"。
DEFAULT_GEMINI_MODEL=gemini-2.5-flash

# 调试功能:
# 启用/禁用为调试目的转储请求/响应数据。
DEBUG_DUMP_ENABLED=false
# 调试转储文件的存储目录。
DEBUG_DUMP_DIR=./debug_dumps

# 控制台输出:
# 启用/禁用服务器的详细控制台日志记录。
CONSOLE_OUTPUT_ENABLED=true
CONSOLE_OUTPUT_VERBOSE=true

# 代理设置:
# 如果您在代理后面，请设置 HTTPS_PROXY 环境变量。
# 可以在启动服务器之前或在此 .env 文件中设置。
# 示例: HTTPS_PROXY=http://your.proxy.server:port
# HTTPS_PROXY=

```

### Note: Translated by Gemini-2.5-flash