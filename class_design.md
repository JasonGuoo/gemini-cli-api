# Class Design: Gemini CLI API

## 1. Introduction

This document provides a detailed design of the classes that will be used to implement the Gemini CLI API server. It outlines the responsibilities of each class, their methods, and the data formats they will handle. This document is intended to be a guide for the implementation of the server.

## 2. Class Designs

### 2.1. `GeminiCLIProcess`

#### 2.1.1. Purpose and Relationships

The `GeminiCLIProcess` class is a wrapper around a single `gemini-cli` subprocess. Its primary responsibility is to manage the lifecycle of the subprocess and to provide a simple interface for sending commands to it and receiving its output. Each instance of this class will represent a single, independent `gemini-cli` process.

This class is managed by the `ProcessPool` class, which creates and maintains a pool of `GeminiCLIProcess` instances. The `APIServer` will not interact with this class directly, but rather through the `ProcessPool`.

#### 2.1.2. Methods

##### `__init__(self, cli_path: str)`

*   **Description:** Initializes a new `GeminiCLIProcess` instance. It sets up the path to the executable but does not start the process.
*   **Input:**
    *   `cli_path` (str): The absolute path to the `gemini-cli` executable.
        *   **Example:** `"/usr/local/bin/gemini-cli"`
*   **Output:** None

##### `start(self)`

*   **Description:** Starts the `gemini-cli` subprocess using Python's `subprocess.Popen`. It will configure the subprocess's `stdin`, `stdout`, and `stderr` to be pipes, allowing the main application to communicate with it programmatically. This method will be called by the `ProcessPool` during initialization.
*   **Input:** None
*   **Output:** None
*   **Implementation Details:** The method will create a `subprocess.Popen` object and store it as an instance variable. It will set `stdin=subprocess.PIPE`, `stdout=subprocess.PIPE`, and `stderr=subprocess.PIPE`.

##### `execute_command(self, command: str, timeout: int) -> Tuple[str, str]`

*   **Description:** Sends a single command to the running `gemini-cli` subprocess and reads its response. This method implements the core communication protocol with the CLI.
*   **Logic:**
    1.  Write the `command` string, followed by a newline character (`\n`), to the subprocess's `stdin`.
    2.  Flush `stdin` to ensure the command is sent immediately.
    3.  Read from the subprocess's `stdout` line by line until a predefined end-of-output delimiter is detected. This delimiter must be a unique string that `gemini-cli` prints after every command execution to signal completion. A UUID could be used for this purpose.
    4.  Simultaneously, read from `stderr` to capture any error messages.
    5.  If the end-of-output delimiter is not detected within the `timeout` period, raise a `TimeoutError`.
    6.  Return the accumulated `stdout` and `stderr` content.
*   **Input:**
    *   `command` (str): The command to be executed.
        *   **Example:** `"/clear"`
    *   `timeout` (int): The number of seconds to wait for a response.
        *   **Example:** `30`
*   **Output:** A tuple containing the standard output and standard error.
    *   **Format:** `(stdout: str, stderr: str)`
    *   **Example:** `("History cleared.", "")`

##### `stop(self)`

*   **Description:** Gracefully terminates the `gemini-cli` subprocess by sending a termination signal.
*   **Input:** None
*   **Output:** None

### 2.2. `ProcessPool`

#### 2.2.1. Purpose and Relationships

The `ProcessPool` class is responsible for managing a fixed-size pool of `GeminiCLIProcess` instances. It ensures that the number of concurrent `gemini-cli` processes does not exceed the specified limit. It provides methods for acquiring and releasing `GeminiCLIProcess` instances from the pool.

This class is used by the `APIServer` to get access to `gemini-cli` processes.

#### 2.2.2. Methods

##### `__init__(self, pool_size: int, cli_path: str)`

*   **Description:** Initializes a new `ProcessPool` instance.
*   **Input:**
    *   `pool_size` (int): The maximum number of `gemini-cli` processes to be managed by the pool.
        *   **Example:** `3`
    *   `cli_path` (str): The absolute path to the `gemini-cli` executable.
        *   **Example:** `"/usr/local/bin/gemini-cli"`
*   **Output:** None

##### `initialize_pool(self)`

*   **Description:** Creates, starts, and populates the pool with `GeminiCLIProcess` instances. It will iterate `pool_size` times, creating a `GeminiCLIProcess` instance, calling its `start()` method, and adding the successfully started process to an internal queue of available processes.
*   **Input:** None
*   **Output:** None

##### `acquire_process(self) -> GeminiCLIProcess`

*   **Description:** Acquires a `GeminiCLIProcess` instance from the pool. If no process is available, it will wait asynchronously until one is released. This will likely be implemented using an `asyncio.Queue`.
*   **Input:** None
*   **Output:** A `GeminiCLIProcess` instance.
    *   **Format:** `GeminiCLIProcess`
    *   **Example:** `<GeminiCLIProcess object at 0x10f4b3d30>`

##### `release_process(self, process: GeminiCLIProcess)`

*   **Description:** Releases a `GeminiCLIProcess` instance back to the pool, making it available for other requests. This will add the process object back to the internal queue.
*   **Input:**
    *   `process` (`GeminiCLIProcess`): The `GeminiCLIProcess` instance to be released.
        *   **Example:** `<GeminiCLIProcess object at 0x10f4b3d30>`
*   **Output:** None

##### `shutdown_pool(self)`

*   **Description:** Stops all the `gemini-cli` processes in the pool by iterating through all created processes and calling their `stop()` method.
*   **Input:** None
*   **Output:** None

### 2.3. `APIServer` (FastAPI Application)

#### 2.3.1. Purpose and Relationships

The `APIServer` is the main entry point of the application. It is a FastAPI application that handles incoming HTTP requests, interacts with the `ProcessPool` to execute `gemini-cli` commands, and formats the responses to be compatible with the OpenAI API.

It uses the `ProcessPool` to get `GeminiCLIProcess` instances and Pydantic models for data validation.

#### 2.3.2. Key Functions/Methods

##### `startup_event()`

*   **Description:** This function is executed when the FastAPI application starts. It initializes the `ProcessPool` by calling its `initialize_pool()` method.
*   **Input:** None
*   **Output:** None

##### `shutdown_event()`

*   **Description:** This function is executed when the FastAPI application shuts down. It shuts down the `ProcessPool` by calling its `shutdown_pool()` method.
*   **Input:** None
*   **Output:** None

##### `chat_completions(request: ChatCompletionRequest)`

*   **Description:** This is the main API endpoint for chat completions. It orchestrates the multi-step interaction with a `gemini-cli` process to ensure a stateless conversation. The logic is as follows:
    1.  **Acquire Process:** Get a `GeminiCLIProcess` instance from the `ProcessPool`.
    2.  **Clear History:** Execute the `/clear` command on the process to ensure no prior history interferes.
    3.  **Execute Prompt:** Send the user's message content to the process. If there are multiple messages, they should be concatenated or handled as per the `gemini-cli`'s expectation for multi-turn input.
    4.  **Get Stats:** Execute the `/stats` command on the same process to retrieve token usage.
    5.  **Parse and Format:** Parse the output from the prompt execution (for the message content) and the `/stats` command (for the usage data).
    6.  **Construct Response:** Build the `ChatCompletionResponse` object in the OpenAI-compatible format.
    7.  **Release Process:** Return the `GeminiCLIProcess` instance to the `ProcessPool`.
    8.  **Return Response:** Send the final JSON response to the client.
*   **Input:**
    *   `request` (`ChatCompletionRequest`): A Pydantic model representing the request body of the `POST /v1/chat/completions` endpoint.
        *   **Example:**
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
*   **Output:** A `ChatCompletionResponse` Pydantic model, which is automatically converted to a JSON response by FastAPI.
    *   **Format:** `ChatCompletionResponse`
    *   **Example:**
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

## 3. Pydantic Models

### 3.1. `ChatMessage`

*   **`role`** (str): The role of the message author. One of "user", "assistant", or "system".
*   **`content`** (str): The content of the message.

### 3.2. `ChatCompletionRequest`

*   **`model`** (str): The model to use for the chat completion. This will be ignored by the server.
*   **`messages`** (List[`ChatMessage`]): A list of messages representing the conversation history.
*   **`stream`** (bool): Whether to stream the response or not.

### 3.3. `Choice`

*   **`index`** (int): The index of the choice in the list of choices.
*   **`message`** (`ChatMessage`): The message generated by the model.
*   **`finish_reason`** (str): The reason the model stopped generating tokens.

### 3.4. `Usage`

*   **`prompt_tokens`** (int): The number of tokens in the prompt.
*   **`completion_tokens`** (int): The number of tokens in the completion.
*   **`total_tokens`** (int): The total number of tokens in the prompt and completion.

### 3.5. `ChatCompletionResponse`

*   **`id`** (str): A unique identifier for the chat completion.
*   **`object`** (str): The type of object, which is always "chat.completion".
*   **`created`** (int): The Unix timestamp of when the chat completion was created.
*   **`model`** (str): The model used for the chat completion.
*   **`choices`** (List[`Choice`]): A list of chat completion choices.
*   **`usage`** (`Usage`): The token usage statistics for the chat completion.
