# Gemini CLI API

**⚠️ This project is currently under active development and is not yet ready for production use. ⚠️**

## Prerequisites

Before running this server, you must have the `gemini-cli` tool installed, and its executable command, `gemini`, must be available in your system's `PATH`.

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

## What is this project?

This project wraps the `gemini` command in a RESTful API server. The primary goal is to make the functionality of `gemini-cli` available over a network interface that is **compatible with the OpenAI API specification**.

By doing this, any application, script, or service that is already designed to work with the OpenAI API (e.g., for `gpt-3.5-turbo` or `gpt-4`) can be pointed at this server to use Google's Gemini models instead, with minimal to no code changes.

### Key Features
-   **OpenAI API Compatibility:** Exposes a `/v1/chat/completions` endpoint that mimics the OpenAI standard.
-   **Stateless Interaction:** Each API call invokes a new `gemini --prompt` process, ensuring each request is handled in a completely stateless manner.
-   **Streaming Support:** Supports real-time, streamed responses for interactive applications, optimized for multi-language content.

## Why Use This for Development?

The primary advantage of this project is for **development and prototyping**.

Google's Gemini models, such as **Gemini 1.5 Pro**, offer a very generous **free tier** for API access. However, integrating with the native Google AI API requires using its specific SDKs and data formats.

This project acts as a bridge, giving you the best of both worlds:
-   **Zero-Cost Development:** You can develop and test your AI-powered applications without incurring API costs by leveraging the Gemini free tier.
-   **Instant Compatibility:** You can use the vast ecosystem of tools, libraries, and applications that are built for the OpenAI API. Simply change the base URL to point to this local server, and your existing code will work.
-   **Production-Ready Path:** Develop for free using this server, and when you're ready to go to production, you can switch to a paid OpenAI model or a dedicated Gemini API endpoint by simply changing the API key and URL, with no other code modifications.

It's the ideal solution for developers who want to build on the OpenAI API standard without the cost, using the power of Gemini models.

## Limitations

Using `gemini-cli` as a backend for an API server introduces several important limitations that users should be aware of:

1.  **Ignored API Parameters:** The `gemini-cli` tool does not support all the parameters available in the official OpenAI Chat Completions API. As a result, parameters like `temperature`, `top_p`, `n`, `stop`, `max_tokens`, `presence_penalty`, `frequency_penalty`, and `logit_bias` will be **accepted but ignored**.

2.  **Model Selection:** The `model` parameter in the API request (`POST /v1/chat/completions`) is used to select the Gemini model. Currently, only `gemini-2.5-flash` and `gemini-2.5-pro` are explicitly supported. If an unsupported model is requested, the server will fall back to the `DEFAULT_GEMINI_MODEL` configured in your `.env` file.

3.  **Token Usage:** The `gemini-cli` does not provide token usage information when using the `--prompt` flag. Therefore, the `usage` field in the API response will always be `null`.

4.  **Performance:** Each API call involves spawning a new command-line subprocess, which introduces more overhead and latency compared to a native API integration.

5.  **Error Handling:** Errors are directly dependent on the output and exit codes of the `gemini` subprocess, which may be less structured or detailed than native API errors.