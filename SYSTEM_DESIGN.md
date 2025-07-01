# System Design: Gemini CLI API

## 1. Introduction

The goal of this project is to expose the existing `gemini-cli` as a RESTful API. This API will be compatible with the OpenAI API specification to allow for easy integration with existing tools and services.

## 2. Goals and Non-Goals

### Goals

*   Create a stateless RESTful API server.
*   The API will be compatible with the OpenAI API format.
*   The API will support streaming responses.
*   The server will be implemented using FastAPI.

### Non-Goals

*   The server will not implement API key management.
*   The server will not implement any user management or authentication.

## 3. System Architecture

The system will consist of a single FastAPI server that acts as the main entry point for all API requests. This server will be responsible for:

1.  Receiving and validating incoming API requests.
2.  Invoking the `gemini-cli` with the `--prompt` flag for each request.
3.  Returning the response from the sub-process to the client.
4.  Handling streaming responses where applicable.
5.  Implementing robust error handling for `gemini-cli` sub-process interactions.
6.  Managing the configuration of the `gemini-cli` executable path.
7.  Implementing basic logging for API requests and sub-process interactions.

### Backend Interaction

To maintain a stateless API, the server will not use a process pool. Instead, for each incoming request, a new `gemini-cli` process is spawned using `gemini --prompt "..."`. This approach simplifies the architecture and ensures that each request is handled in complete isolation.

For each request:
1.  The FastAPI server will construct a single prompt string from the `messages` array in the request body.
2.  The server will execute the `gemini --prompt "<prompt>"` command.
3.  The `stdout` and `stderr` of the process will be captured.
4.  The captured output is then formatted into the OpenAI-compatible response.

## 4. API Design

The API will adhere to the OpenAI API specification.

### `POST /v1/chat/completions`

This endpoint will be used for chat-based interactions.

**Request Body:**

```json
{
  "model": "gemini-cli",
  "messages": [
    {
      "role": "user",
      "content": "Hello, who are you?"
    }
  ],
  "stream": false
}
```

**Response Body (non-streaming):**

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "gemini-cli",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "I am a large language model, trained by Google."
    },
    "finish_reason": "stop"
  }],
  "usage": null
}
```

**Response Body (streaming):**

When `stream` is set to `true`, the API will return a stream of server-sent events (SSE).

## 5. Technology Stack

*   **Web Framework:** FastAPI
*   **Backend:** The existing `gemini-cli` executable.
*   **Language:** Python

## 6. Limitations

*   **Model Parameter:** The `model` parameter in the API request will be ignored. The underlying `gemini-cli` will use its own configured model.
*   **Ignored Parameters:** Other OpenAI API parameters (e.g., `temperature`, `top_p`, etc.) will be ignored.
*   **Token Usage Information:** The `usage` field in the API response will be `null`, as the `gemini-cli` does not provide token counts when using the `--prompt` flag.

## 7. Project Structure and Key Components

### Main Components

*   **`main.py`**: The FastAPI application, handling HTTP requests and invoking the `gemini-cli`.
*   **`services/gemini_cli.py`**: Contains the function for executing the `gemini --prompt` command.
*   **`models.py`**: Pydantic models for the API requests and responses.
*   **`config.py`**: Configuration settings.