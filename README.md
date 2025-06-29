# Gemini CLI API

**⚠️ This project is currently under active development and is not yet ready for production use. ⚠️**

## What is `gemini-cli`?

`gemini-cli` is a powerful, unofficial command-line interface (CLI) that allows users to interact directly with Google's Gemini family of large language models from their terminal. It provides a convenient way to have conversations, manage history, and access the capabilities of Gemini without needing a graphical user interface.

## What is this project?

This project wraps the `gemini-cli` tool in a RESTful API server. The primary goal is to make the functionality of `gemini-cli` available over a network interface that is **compatible with the OpenAI API specification**.

By doing this, any application, script, or service that is already designed to work with the OpenAI API (e.g., for `gpt-3.5-turbo` or `gpt-4`) can be pointed at this server to use Google's Gemini models instead, with minimal to no code changes.

### Key Features
-   **OpenAI API Compatibility:** Exposes a `/v1/chat/completions` endpoint that mimics the OpenAI standard.
-   **Stateless Interaction:** Manages underlying `gemini-cli` processes to ensure each API call is treated as a separate, stateless conversation.
-   **Streaming Support:** Supports real-time, streamed responses for interactive applications.
-   **Concurrent Requests:** Utilizes a process pool to handle multiple API requests simultaneously.

## Limitations

Using `gemini-cli` as a backend for an API server introduces several important limitations that users should be aware of:

1.  **Ignored API Parameters:** The `gemini-cli` tool does not support all the parameters available in the official OpenAI Chat Completions API. As a result, the following parameters in your API calls will be **accepted but ignored**:
    *   `model` (The underlying Gemini model is configured in the `gemini-cli` tool itself).
    *   `temperature`, `top_p`, `n`, `stop`, `max_tokens`, `presence_penalty`, `frequency_penalty`, `logit_bias`, etc.
    The API will simply pass the prompt to `gemini-cli` and return whatever it generates based on its own internal settings.

2.  **Token Usage:** Token count information (`prompt_tokens`, `completion_tokens`, `total_tokens`) is retrieved by running a separate `/stats` command within the CLI after a response is generated. While this provides a good estimate, it may not be perfectly analogous to the official OpenAI API's token accounting.

3.  **Performance:** Each API call involves interacting with a command-line subprocess, which introduces more overhead than a native API integration.

4.  **Error Handling:** Errors will be dependent on the output of the `gemini-cli` subprocess, which may be less structured than native API errors.