# System Design: Gemini CLI API

## 1. Introduction

The goal of this project is to expose the existing `gemini-cli` as a RESTful API. This API will be compatible with the OpenAI API specification to allow for easy integration with existing tools and services.

## 2. Goals and Non-Goals

### Goals

*   Create a stateless RESTful API server.
*   The server will manage a pool of three backend sub-processes for chat completions.
*   The API will be compatible with the OpenAI API format.
*   The API will support streaming responses.
*   The server will be implemented using FastAPI.

### Non-Goals

*   The server will not implement API key management.
*   The server will not implement any user management or authentication.

## 3. System Architecture

The system will consist of a single FastAPI server that acts as the main entry point for all API requests. This server will be responsible for:

1.  Receiving and validating incoming API requests.
2.  Forwarding requests to the backend `gemini-cli` sub-process.
3.  Returning the response from the sub-process to the client.
4.  Handling streaming responses where applicable.
5.  Implementing robust error handling for `gemini-cli` sub-process interactions, including:
    *   Capturing `stderr` for diagnostic information.
    *   Handling non-zero exit codes from the sub-process.
    *   Implementing timeouts for `gemini-cli` invocations to prevent hanging.
    *   Returning appropriate HTTP error codes (e.g., 500 Internal Server Error) to the client for sub-process failures.
6.  Managing the configuration of the `gemini-cli` executable path (e.g., via environment variables).
7.  Implementing basic logging for API requests and sub-process interactions.

### Backend Sub-processes

To maintain a stateless API and handle concurrent requests, the FastAPI server will manage a pool of `gemini-cli` sub-processes. This ensures isolation and avoids complex state management within the FastAPI server, while also limiting the number of concurrent `gemini-cli` instances.

For each request:
1.  The FastAPI server will obtain an available `gemini-cli` process from the pool. If no process is immediately available, the request will wait until one becomes free.
2.  The FastAPI server will construct the `messages` array (from the request body) into a format `gemini-cli` can consume (e.g., JSON string passed via standard input).
3.  The formatted `messages` will be passed to the `gemini-cli` process.
4.  The output (standard output for the response, standard error for errors) will be captured.
5.  Once the response is received or an error occurs, the `gemini-cli` process will be returned to the pool for reuse.

This approach assumes that the `gemini-cli` can accept and process the full conversation history as a single input for each invocation, effectively treating each API request as a new, self-contained conversation. The `/clear` command in `gemini-cli` is considered relevant for its interactive CLI use, not for its programmatic interaction as a backend for this API.

### Process Pool Management

To enforce the concurrency limit of three `gemini-cli` sub-processes, a process pool will be implemented.

1.  **Initialization:** Upon server startup, three `gemini-cli` sub-processes will be launched and added to a pool of available processes. Each process will be kept alive and ready to receive commands.
2.  **Acquisition:** When an API request for chat completion (`POST /v1/chat/completions`) arrives, the FastAPI server will attempt to acquire a `gemini-cli` process from the pool.
    *   If an idle process is available, it will be immediately assigned to handle the request.
    *   If all processes are currently busy, the incoming request will be queued and will wait until a process becomes available.
3.  **Execution:** The acquired `gemini-cli` process will execute the chat completion command with the provided messages.
4.  **Release:** Once the `gemini-cli` process completes its task (either successfully or with an error), it will be returned to the pool, making it available for the next queued request.
5.  **Health Checks (Future Consideration):** Mechanisms for periodically checking the health of processes in the pool and replacing any that become unresponsive or crash will be considered for future enhancements.

This process pool management ensures that the system adheres to the maximum concurrency limit while efficiently reusing `gemini-cli` instances, reducing the overhead of repeatedly launching new processes.

## 4. API Design

The API will adhere to the OpenAI API specification. The initial implementation will focus on the most common endpoint:

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
  "usage": {
    "prompt_tokens": 9,
    "completion_tokens": 12,
    "total_tokens": 21
  }
}
```

**Response Body (streaming):**

When `stream` is set to `true`, the API will return a stream of server-sent events (SSE).

## 5. Technology Stack

*   **Web Framework:** FastAPI
*   **Backend:** The existing `gemini-cli` executable.
*   **Language:** Python

## 6. Future Considerations

*   **Load Balancing:** For higher volumes, a load balancer could be placed in front of multiple instances of the API server.
*   **Error Handling:** A robust error handling and logging mechanism will be needed to manage the sub-processes effectively.

## 7. Limitations

*   **Model Parameter:** The `model` parameter in the API request (`POST /v1/chat/completions`) will be largely symbolic. The underlying `gemini-cli` will use its own configured or default model, and the API will not support dynamic selection of different models.
*   **Ignored Parameters:** Other parameters specified in the OpenAI chat completions API (e.g., `temperature`, `top_p`, `n`, `stop`, `max_tokens`, `presence_penalty`, `frequency_penalty`, `logit_bias`, `user`) will be ignored by the FastAPI server unless the `gemini-cli` provides specific command-line arguments or configuration options to control these aspects. If `gemini-cli` does not expose these controls, these parameters will have no effect on the generated response.
*   **Token Usage Information:** The `usage` field (containing `prompt_tokens`, `completion_tokens`, and `total_tokens`) in the API response will be supported, as the `gemini-cli` provides this information in its output. By using '/stats' command in the 'gemini-cli'.

## 8. Project Structure and Key Components

### Main Classes

*   **`GeminiCLIProcess`**:
    *   **Purpose**: Encapsulates a single `gemini-cli` sub-process. Manages its lifecycle (start, stop) and interaction (sending commands, receiving output).
    *   **Attributes**:
        *   `process`: The `subprocess.Popen` object.
        *   `is_busy`: Boolean flag indicating if the process is currently handling a request.
        *   `id`: Unique identifier for the process.
    *   **Methods**:
        *   `__init__(self, cli_path: str)`: Initializes the process with the path to the `gemini-cli` executable.
        *   `start(self)`: Starts the `gemini-cli` sub-process.
        *   `execute_command(self, command: str, timeout: int) -> Tuple[str, str]`: Sends a command to the `gemini-cli` and captures its stdout and stderr. Implements a timeout.
        *   `stop(self)`: Terminates the `gemini-cli` sub-process.

*   **`ProcessPool`**:
    *   **Purpose**: Manages a pool of `GeminiCLIProcess` instances, ensuring a fixed number of concurrent `gemini-cli` processes and handling their acquisition and release.
    *   **Attributes**:
        *   `pool_size`: Maximum number of `gemini-cli` processes in the pool (e.g., 3).
        *   `processes`: List of `GeminiCLIProcess` objects.
        *   `available_processes`: An `asyncio.Queue` or similar structure to manage available processes.
        *   `cli_path`: Path to the `gemini-cli` executable.
    *   **Methods**:
        *   `__init__(self, pool_size: int, cli_path: str)`: Initializes the pool with a specified size and CLI path.
        *   `initialize_pool(self)`: Starts all `gemini-cli` processes and adds them to the available queue.
        *   `acquire_process(self) -> GeminiCLIProcess`: Asynchronously waits for and returns an available `GeminiCLIProcess` from the pool.
        *   `release_process(self, process: GeminiCLIProcess)`: Returns a `GeminiCLIProcess` to the available queue.
        *   `shutdown_pool(self)`: Stops all processes in the pool.

*   **`APIServer` (FastAPI Application)**:
    *   **Purpose**: The main FastAPI application, handling HTTP requests and interacting with the `ProcessPool`.
    *   **Attributes**:
        *   `app`: The FastAPI application instance.
        *   `process_pool`: An instance of `ProcessPool`.
    *   **Key Functions/Methods**:
        *   `@app.on_event("startup")`: Asynchronous function to initialize the `ProcessPool` when the server starts.
        *   `@app.on_event("shutdown")`: Asynchronous function to shut down the `ProcessPool` when the server stops.
        *   `@app.post("/v1/chat/completions")`: The main API endpoint for chat completions.
            *   Acquires a `GeminiCLIProcess` from the `process_pool`.
            *   Constructs the command for `gemini-cli` based on the request body.
            *   Executes the command using the acquired process.
            *   Parses the `gemini-cli` output and formats it into an OpenAI-compatible response.
            *   Handles streaming responses if `stream` is true in the request.
            *   Releases the `GeminiCLIProcess` back to the `process_pool`.
            *   Implements error handling for `gemini-cli` execution and returns appropriate HTTP responses.

### Overall Flow

1.  **Server Startup**:
    *   FastAPI `startup` event triggers `ProcessPool.initialize_pool()`.
    *   `ProcessPool` launches `pool_size` (e.g., 3) `GeminiCLIProcess` instances and makes them available.
2.  **Incoming Request (`POST /v1/chat/completions`)**:
    *   The FastAPI endpoint handler is invoked.
    *   It calls `process_pool.acquire_process()` to get an available `gemini-cli` instance. If none are available, the request waits.
    *   **Statelessness Enforcement**: The acquired `gemini-cli` process first executes the `/clear` command to ensure a clean state, making each API request independent.
    *   The request payload (messages) is transformed into a `gemini-cli` command.
    *   `GeminiCLIProcess.execute_command()` is called to run the chat completion command.
    *   The `gemini-cli` output (response and potential errors) is captured.
    *   **Token Usage Retrieval**: After the chat completion, the `gemini-cli` process executes the `/stats` command to retrieve token usage information.
    *   The `gemini-cli` output (chat response and stats) is parsed.
    *   The `GeminiCLIProcess` is returned to the pool via `process_pool.release_process()`.
    *   An OpenAI-compatible response, including the retrieved token usage, is sent back to the client.
3.  **Server Shutdown**:
    *   FastAPI `shutdown` event triggers `ProcessPool.shutdown_pool()`.
    *   `ProcessPool` gracefully terminates all `GeminiCLIProcess` instances.

### Request Handling Logic (`APIServer`'s `POST /v1/chat/completions` endpoint)

The detailed logic for handling an incoming chat completion request will be as follows:

1.  **Acquire Process**:
    *   Asynchronously acquire a `GeminiCLIProcess` instance from the `ProcessPool`. This call will block if no processes are immediately available, ensuring adherence to the concurrency limit.
    *   Implement a timeout for acquiring the process to prevent indefinite waiting. If a process cannot be acquired within a reasonable time, return an appropriate HTTP error (e.g., 503 Service Unavailable).

2.  **Ensure Statelessness (`/clear`)**:
    *   Once a `GeminiCLIProcess` is acquired, immediately execute the `/clear` command on it. This ensures that any previous conversation history within that specific `gemini-cli` instance is cleared, making each API request truly stateless.
    *   Handle potential errors during the `/clear` command execution. If `/clear` fails, it might indicate an issue with the `gemini-cli` process, and the process should potentially be marked as unhealthy or replaced.

3.  **Execute Chat Completion**:
    *   Construct the `gemini-cli` command from the incoming request's `messages` array. This will likely involve serializing the messages into a format `gemini-cli` expects (e.g., JSON string).
    *   Execute this command using the `GeminiCLIProcess.execute_command()` method.
    *   Capture the standard output (for the model's response) and standard error (for any `gemini-cli` errors or diagnostic messages).
    *   Implement robust error handling for the command execution, including:
        *   Checking the exit code of the `gemini-cli` process.
        *   Parsing `stderr` for specific error messages.
        *   Handling timeouts during the chat completion.

4.  **Retrieve Token Usage (`/stats`)**:
    *   After the chat completion command, execute the `/stats` command on the same `GeminiCLIProcess` instance.
    *   Parse the output of the `/stats` command to extract `prompt_tokens`, `completion_tokens`, and `total_tokens`.
    *   Handle cases where `/stats` might not return the expected format or fails.

5.  **Format Response**:
    *   Parse the chat completion output from `gemini-cli` into the `message` field of the OpenAI-compatible response.
    *   Populate the `usage` field of the OpenAI-compatible response with the token usage information obtained from the `/stats` command.
    *   Generate a unique `id` for the chat completion.
    *   Set `object`, `created`, `model`, `choices`, and `finish_reason` fields as per the OpenAI API specification.

6.  **Handle Streaming (if `stream=true`)**:
    *   If the incoming request has `stream: true`, a response should be a stream of Server-Sent Events (SSE).
    *   This will require careful handling of the `gemini-cli` output to stream chunks of the response as they become available, rather than waiting for the entire response.
    *   Token usage for streaming might be more complex to report incrementally or might be reported at the end of the stream.

7.  **Release Process**:
    *   Regardless of success or failure, ensure the `GeminiCLIProcess` is released back to the `ProcessPool` using `process_pool.release_process()`. This is crucial for resource management and preventing deadlocks.

8.  **Return HTTP Response**:
    *   Return the formatted OpenAI-compatible JSON response (or stream) to the client.
    *   If any errors occurred during the process (e.g., `gemini-cli` execution error, timeout, parsing error), return an appropriate HTTP error status code (e.g., 500 Internal Server Error, 400 Bad Request) along with a descriptive error message.

## 9. Proposed Project Structure

Based on the logical components outlined above, a practical project structure would be as follows. This structure separates concerns, making the codebase easier to navigate and maintain.

```
/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI app, endpoints, and startup/shutdown events
│   ├── services/
│   │   ├── __init__.py
│   │   ├── gemini_cli.py    # GeminiCLIProcess class
│   │   └── process_pool.py  # ProcessPool class
│   ├── models.py        # Pydantic models for API requests/responses
│   └── config.py        # Configuration settings
├── .env                 # For environment variables like the CLI path
├── requirements.txt
└── SYSTEM_DESIGN.md
```

*   **`app/main.py`**: This will be the main entry point for the FastAPI application. It will define the API endpoints (like `/v1/chat/completions`), and include the startup and shutdown event handlers to manage the process pool.
*   **`app/services/gemini_cli.py`**: This file will contain the `GeminiCLIProcess` class, responsible for managing a single `gemini-cli` subprocess.
*   **`app/services/process_pool.py`**: This file will house the `ProcessPool` class, which manages the lifecycle of multiple `GeminiCLIProcess` instances.
*   **`app/models.py`**: This will define the Pydantic models for the API request and response bodies, ensuring they conform to the OpenAI specification.
*   **`app/config.py`**: This file will handle application configuration, such as loading the path to the `gemini-cli` executable from environment variables.
*   **`.env`**: This file will store environment-specific variables, such as the path to the `gemini-cli` executable, and will be loaded by the application at startup.
