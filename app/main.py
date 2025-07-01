from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse
from app.models import ChatCompletionRequest, ChatCompletionResponse, ChatMessage, Choice, Usage, Delta
from app.services.gemini_cli import execute_gemini_command
from app.config import GEMINI_CLI_PATH, DEBUG_DUMP_ENABLED, DEBUG_DUMP_DIR, DEFAULT_GEMINI_MODEL
import asyncio
import time
import json
import os
import datetime
import uuid
import re

app = FastAPI(
    title="Gemini CLI OpenAI Compatible API",
    description="A RESTful API that wraps the gemini-cli tool to provide an OpenAI-compatible interface.",
    version="0.1.0",
)

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
    print("🚀 Starting Gemini CLI API server...")
    print(f"🔧 CLI path: {GEMINI_CLI_PATH}")
    print(f"🐛 Debug dumps: {'enabled' if DEBUG_DUMP_ENABLED else 'disabled'}")
    print(f"🤖 Default Gemini Model: {DEFAULT_GEMINI_MODEL}")

@app.on_event("shutdown")
async def shutdown_event():
    print("🛑 Shutting down Gemini CLI API server...")

# Allowed models for validation
ALLOWED_GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.5-pro"]

async def generate_stream_response(request: ChatCompletionRequest, debug_dump_data: dict):
    request_id = debug_dump_data["request_id"]
    full_prompt = "\n".join([msg.content for msg in request.messages if msg.role == "user"])

    # Determine the model to use
    model_to_use = DEFAULT_GEMINI_MODEL
    if request.model and request.model in ALLOWED_GEMINI_MODELS:
        model_to_use = request.model

    try:
        # Send initial chunk with role
        initial_delta = Delta(role="assistant", content="")
        initial_choice = Choice(index=0, delta=initial_delta, finish_reason=None)
        initial_response = ChatCompletionResponse(
            id=f"chatcmpl-{request_id}",
            created=int(time.time()),
            model=model_to_use,
            choices=[initial_choice],
            usage=None
        )
        yield f"data: {json.dumps(initial_response.dict(exclude_unset=True))}\n\n"

        async for stdout_chunk, stderr_chunk in execute_gemini_command(full_prompt, model_name=model_to_use, stream=True):
            if stderr_chunk:
                print(f"Error during stream: {stderr_chunk}")

            if stdout_chunk:
                # Send subsequent chunks with content
                delta_chunk = Delta(content=stdout_chunk)
                choice_chunk = Choice(index=0, delta=delta_chunk, finish_reason=None)
                response_chunk = ChatCompletionResponse(
                    id=f"chatcmpl-{request_id}",
                    created=int(time.time()),
                    model=model_to_use,
                    choices=[choice_chunk],
                    usage=None
                )
                yield f"data: {json.dumps(response_chunk.dict(exclude_unset=True))}\n\n"

        # Send final chunk with finish_reason
        final_delta = Delta(content=None)
        final_choice = Choice(index=0, delta=final_delta, finish_reason="stop")
        final_response = ChatCompletionResponse(
            id=f"chatcmpl-{request_id}",
            created=int(time.time()),
            model=model_to_use,
            choices=[final_choice],
            usage=None
        )
        yield f"data: {json.dumps(final_response.dict(exclude_unset=True))}\n\n"
        yield "data: [DONE]\n\n"

    except Exception as e:
        print(f"An error occurred during streaming: {e}")
        error_response = {
            "error": {
                "message": str(e),
                "type": "stream_error",
                "param": None,
                "code": None
            }
        }
        yield f"data: {json.dumps(error_response)}\n\n"
        yield "data: [DONE]\n\n"

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    request_id = str(uuid.uuid4())
    debug_dump_data = {
        "request_id": request_id,
        "timestamp_start": datetime.datetime.now().isoformat(),
        "request_body": request.dict(),
        "cli_interactions": []
    }

    # Determine the model to use
    model_to_use = DEFAULT_GEMINI_MODEL
    if request.model and request.model in ALLOWED_GEMINI_MODELS:
        model_to_use = request.model

    try:
        full_prompt = "\n".join([msg.content for msg in request.messages if msg.role == "user"])

        if request.stream:
            return StreamingResponse(generate_stream_response(request, debug_dump_data), media_type="text/event-stream")
        else:
            stdout, stderr = await execute_gemini_command(full_prompt, model_name=model_to_use).__anext__()

            if stderr:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Gemini CLI error: {stderr}")

            response_message = ChatMessage(role="assistant", content=stdout)
            choice = Choice(index=0, message=response_message, finish_reason="stop")
            response = ChatCompletionResponse(
                id=f"chatcmpl-{request_id}",
                created=int(time.time()),
                model=model_to_use,
                choices=[choice],
                usage=None,
            )

            return JSONResponse(content=response.dict())

    except Exception as e:
        print(f"An unexpected error occurred for request {request_id}: {e}")
        debug_dump_data["error"] = str(e)
        await dump_debug_info(f"{request_id}_error.json", debug_dump_data)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")
