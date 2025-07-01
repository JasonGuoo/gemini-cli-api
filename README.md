# Gemini CLI API

**⚠️ This project is currently under active development and is not yet ready for production use. ⚠️**

## Prerequisites

Before running this server, you must have the `gemini-cli` tool installed, and its executable command, `gemini`, must be available in your system's `PATH`.

## What is this project?

This project provides a **RESTful API compatible with the OpenAI API specification**, by wrapping the `gemini-cli` tool. This allows developers to leverage Google's powerful Gemini models using existing OpenAI-compatible applications and libraries, with minimal to no code changes.

### The Free Tier Advantage: Gemini CLI vs. Gemini API

A key differentiator of this project is its ability to utilize the **generous free tier** offered by Google AI Studio (which `gemini-cli` accesses). This provides a significant advantage for development and prototyping:

| Feature                     | Gemini CLI (via Google AI Studio Free Tier) | Direct Gemini API (Paid Tier) |
| :-------------------------- | :------------------------------------------ | :---------------------------- |
| **Cost**                    | Free                                        | Pay-as-you-go (usage-based)   |
| **Requests per user per minute** | 120                                         | Significantly higher          |
| **Requests per user per day**    | 1000 (Individuals), 1500 (Standard)         | Significantly higher          |

This means you can develop and extensively test your AI-powered applications without incurring API costs, making it an ideal solution for:

-   **Zero-Cost Development:** Build and test applications leveraging Gemini models without spending money on API calls.
-   **Instant Compatibility:** Seamlessly integrate with the vast ecosystem of OpenAI-compatible tools and libraries by simply changing the API base URL.
-   **Production-Ready Path:** Develop for free, and easily transition to a paid OpenAI model or direct Gemini API integration for production by updating API keys and URLs, without major code refactoring.



### Key Features
-   **OpenAI API Compatibility:** Exposes a `/v1/chat/completions` endpoint that mimics the OpenAI standard.
-   **Stateless Interaction:** Each API call invokes a new `gemini --prompt` process, ensuring each request is handled in a completely stateless manner.
-   **Streaming Support:** Supports real-time, streamed responses for interactive applications, optimized for multi-language content.

## Limitations

Using `gemini-cli` as a backend for an API server introduces several important limitations that users should be aware of:

1.  **Ignored API Parameters:** The `gemini-cli` tool does not support all the parameters available in the official OpenAI Chat Completions API. As a result, parameters like `temperature`, `top_p`, `n`, `stop`, `max_tokens`, `presence_penalty`, `frequency_penalty`, and `logit_bias` will be **accepted but ignored**.

2.  **Model Selection:** The `model` parameter in the API request (`POST /v1/chat/completions`) is used to select the Gemini model. Currently, only `gemini-2.5-flash` and `gemini-2.5-pro` are explicitly supported. If an unsupported model is requested, the server will fall back to the `DEFAULT_GEMINI_MODEL` configured in your `.env` file.

3.  **Token Usage:** The `gemini-cli` does not provide token usage information when using the `--prompt` flag. Therefore, the `usage` field in the API response will always be `null`.

4.  **Performance:** Each API call involves spawning a new command-line subprocess, which introduces more overhead and latency compared to a native API integration.

5.  **Error Handling:** Errors are directly dependent on the output and exit codes of the `gemini` subprocess, which may be less structured or detailed than native API errors.

## Configuration

This server leverages environment variables for its configuration, which can be conveniently managed using a `.env` file in the project root. When the server starts, it automatically loads these variables, making them accessible to both the FastAPI application and the underlying `gemini` CLI processes.

Here are some key configuration options you can set in your `.env` file:

```dotenv
# Your Gemini API key (required for gemini-cli to function)
GEMINI_API_KEY=your_api_key_here

# Your Google Cloud Project ID (if gemini-cli requires it)
# GOOGLE_CLOUD_PROJECT=your_project_id

# Server Port: The port on which the FastAPI server will listen.
# Defaults to 8000 if not specified.
PORT=8000

# Default Gemini Model: The model to use if the client does not specify a supported model
# or specifies an invalid one. Supported values are "gemini-2.5-flash" or "gemini-2.5-pro".
# Defaults to "gemini-2.5-flash".
DEFAULT_GEMINI_MODEL=gemini-2.5-flash

# Debugging Features:
# Enable/disable dumping of request/response data for debugging purposes.
DEBUG_DUMP_ENABLED=false
# Directory where debug dumps will be stored.
DEBUG_DUMP_DIR=./debug_dumps

# Console Output:
# Enable/disable verbose console logging from the server.
CONSOLE_OUTPUT_ENABLED=true
CONSOLE_OUTPUT_VERBOSE=true
```