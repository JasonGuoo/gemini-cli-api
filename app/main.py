from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse
from app.models import ChatCompletionRequest, ChatCompletionResponse, ChatMessage, Choice, Usage
from app.services.process_pool import ProcessPool
from app.config import GEMINI_CLI_PATH, DEBUG_DUMP_ENABLED, DEBUG_DUMP_DIR
import asyncio
import time
import json
import os
import datetime

app = FastAPI(
    title="Gemini CLI OpenAI Compatible API",
    description="A RESTful API that wraps the gemini-cli tool to provide an OpenAI-compatible interface.",
    version="0.1.0",
)

# Global instance of the ProcessPool
process_pool: ProcessPool = None

async def dump_debug_info(filename: str, data: dict):
    """Dumps debug information to a JSON file."""
    if not DEBUG_DUMP_ENABLED:
        return
    
    filepath = os.path.join(DEBUG_DUMP_DIR, filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

@app.on_event("startup")
async def startup_event():
    global process_pool
    print("Application startup: Initializing ProcessPool...")
    try:
        # Initialize the ProcessPool with a size of 3 (as per design) and the detected CLI path
        process_pool = ProcessPool(pool_size=3, cli_path=GEMINI_CLI_PATH)
        await process_pool.initialize_pool()
        print("ProcessPool initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize ProcessPool: {e}")
        # Depending on the desired behavior, you might want to exit the application
        # if the pool cannot be initialized.
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to start application: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    global process_pool
    if process_pool:
        print("Application shutdown: Shutting down ProcessPool...")
        await process_pool.shutdown_pool()
        print("ProcessPool shutdown complete.")

async def generate_stream_response(process, request: ChatCompletionRequest, debug_dump_data: dict):
    request_id = debug_dump_data["request_id"]
    
    # 1. Clear History
    clear_stdout, clear_stderr = await process.execute_command("/clear", timeout=5).__anext__() # Get first (and only) result
    debug_dump_data["cli_interactions"].append({
        "command": "/clear",
        "stdout": clear_stdout,
        "stderr": clear_stderr,
        "timestamp": datetime.datetime.now().isoformat()
    })
    if clear_stderr: 
        print(f"Warning: Stderr during /clear: {clear_stderr}")
        yield f"data: {json.dumps({"error": f"CLI clear error: {clear_stderr}"})}\n\n"

    # 2. Execute Prompt (streaming)
    full_prompt = "\n".join([msg.content for msg in request.messages if msg.role == "user"])
    
    # Yield chunks as SSE
    async for stdout_chunk, stderr_chunk in process.execute_command(full_prompt, timeout=60, stream=True):
        if stdout_chunk:
            response_message = ChatMessage(role="assistant", content=stdout_chunk)
            choice = Choice(index=0, message=response_message, finish_reason=None) # finish_reason will be sent at the end
            response = ChatCompletionResponse(
                id=f"chatcmpl-{request_id}",
                created=int(time.time()),
                model=request.model,
                choices=[choice],
                usage=Usage(prompt_tokens=0, completion_tokens=0, total_tokens=0) # Usage will be sent at the end
            )
            yield f"data: {json.dumps(response.dict(exclude_unset=True))}\n\n"
            debug_dump_data["cli_interactions"].append({
                "command": "prompt_stream_chunk",
                "stdout": stdout_chunk,
                "stderr": stderr_chunk,
                "timestamp": datetime.datetime.now().isoformat()
            })
        if stderr_chunk:
            print(f"Error during chat command execution (stream): {stderr_chunk}")
            yield f"data: {json.dumps({"error": f"CLI stream error: {stderr_chunk}"})}\n\n"
            debug_dump_data["cli_interactions"].append({
                "command": "prompt_stream_error",
                "stdout": stdout_chunk,
                "stderr": stderr_chunk,
                "timestamp": datetime.datetime.now().isoformat()
            })

    # 3. Get Stats after stream finishes
    stats_stdout, stats_stderr = await process.execute_command("/stats", timeout=5).__anext__() # Get first (and only) result
    debug_dump_data["cli_interactions"].append({
        "command": "/stats",
        "stdout": stats_stdout,
        "stderr": stats_stderr,
        "timestamp": datetime.datetime.now().isoformat()
    })
    if stats_stderr:
        print(f"Warning: Stderr during /stats: {stats_stderr}")
        yield f"data: {json.dumps({"error": f"CLI stats error: {stats_stderr}"})}\n\n"

    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0

    try:
        stats_data = json.loads(stats_stdout)
        prompt_tokens = stats_data.get("prompt_tokens", 0)
        completion_tokens = stats_data.get("completion_tokens", 0)
        total_tokens = stats_data.get("total_tokens", 0)
    except json.JSONDecodeError:
        print(f"Warning: Could not parse /stats output as JSON: {stats_stdout}")

    # Send final usage and finish_reason
    final_usage = Usage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )
    final_choice = Choice(index=0, message=ChatMessage(role="assistant", content=""), finish_reason="stop")
    final_response = ChatCompletionResponse(
        id=f"chatcmpl-{request_id}",
        created=int(time.time()),
        model=request.model,
        choices=[final_choice],
        usage=final_usage,
    )
    yield f"data: {json.dumps(final_response.dict(exclude_unset=True))}\n\n"
    yield "data: [DONE]\n\n"

    debug_dump_data["final_response"] = final_response.dict(exclude_unset=True)
    await dump_debug_info(f"{request_id}_stream.json", debug_dump_data)

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    request_id = str(uuid.uuid4())
    debug_dump_data = {
        "request_id": request_id,
        "timestamp_start": datetime.datetime.now().isoformat(),
        "request_body": request.dict(),
        "cli_interactions": []
    }

    process = None
    try:
        # 1. Acquire Process
        process = await process_pool.acquire_process()
        print(f"Acquired process {process} for request {request_id}.")

        if request.stream:
            return StreamingResponse(generate_stream_response(process, request, debug_dump_data), media_type="text/event-stream")
        else:
            # Non-streaming logic (existing)
            # 2. Clear History
            clear_stdout, clear_stderr = await process.execute_command("/clear", timeout=5).__anext__() # Get first (and only) result
            debug_dump_data["cli_interactions"].append({
                "command": "/clear",
                "stdout": clear_stdout,
                "stderr": clear_stderr,
                "timestamp": datetime.datetime.now().isoformat()
            })
            if clear_stderr: # Check for errors during clear
                print(f"Warning: Stderr during /clear: {clear_stderr}")

            # 3. Execute Prompt
            full_prompt = "\n".join([msg.content for msg in request.messages if msg.role == "user"])
            chat_stdout, chat_stderr = await process.execute_command(full_prompt, timeout=60).__anext__() # Get first (and only) result
            debug_dump_data["cli_interactions"].append({
                "command": "prompt",
                "stdout": chat_stdout,
                "stderr": chat_stderr,
                "timestamp": datetime.datetime.now().isoformat()
            })

            if chat_stderr:
                print(f"Error during chat command execution: {chat_stderr}")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Gemini CLI error: {chat_stderr}")

            # 4. Get Stats
            stats_stdout, stats_stderr = await process.execute_command("/stats", timeout=5).__anext__() # Get first (and only) result
            debug_dump_data["cli_interactions"].append({
                "command": "/stats",
                "stdout": stats_stdout,
                "stderr": stats_stderr,
                "timestamp": datetime.datetime.now().isoformat()
            })
            if stats_stderr:
                print(f"Warning: Stderr during /stats: {stats_stderr}")

            # 5. Parse and Format
            prompt_tokens = 0
            completion_tokens = 0
            total_tokens = 0

            try:
                stats_data = json.loads(stats_stdout)
                prompt_tokens = stats_data.get("prompt_tokens", 0)
                completion_tokens = stats_data.get("completion_tokens", 0)
                total_tokens = stats_data.get("total_tokens", 0)
            except json.JSONDecodeError:
                print(f"Warning: Could not parse /stats output as JSON: {stats_stdout}")
                pass

            # 6. Construct Response
            response_message = ChatMessage(role="assistant", content=chat_stdout.strip())
            usage = Usage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            )
            choice = Choice(index=0, message=response_message, finish_reason="stop")

            response = ChatCompletionResponse(
                id=f"chatcmpl-{request_id}",
                created=int(time.time()),
                model=request.model, # Use the model name from the request
                choices=[choice],
                usage=usage,
            )
            debug_dump_data["final_response"] = response.dict()
            await dump_debug_info(f"{request_id}_non_stream.json", debug_dump_data)

            return JSONResponse(content=response.dict())

    except TimeoutError as e:
        print(f"Request {request_id} timed out: {e}")
        debug_dump_data["error"] = str(e)
        await dump_debug_info(f"{request_id}_error.json", debug_dump_data)
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(e))
    except RuntimeError as e:
        print(f"Runtime error with Gemini CLI process for request {request_id}: {e}")
        debug_dump_data["error"] = str(e)
        await dump_debug_info(f"{request_id}_error.json", debug_dump_data)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred for request {request_id}: {e}")
        debug_dump_data["error"] = str(e)
        await dump_debug_info(f"{request_id}_error.json", debug_dump_data)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")
    finally:
        # 7. Release Process
        if process:
            await process_pool.release_process(process)
            print(f"Released process {process} for request {request_id}.")
