#!/usr/bin/env python3
"""
简化版 Gemini CLI OpenAI 兼容 API
使用 -p 参数直接调用，无需复杂的进程池管理
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import StreamingResponse
from app.models import ChatCompletionRequest, ChatCompletionResponse, ChatMessage, Choice, Usage
from app.services.gemini_simple import SimplifiedGeminiCLI
from app.config import GEMINI_CLI_PATH, DEBUG_DUMP_ENABLED, DEBUG_DUMP_DIR
import asyncio
import time
import json
import os
import datetime
import uuid

app = FastAPI(
    title="Gemini CLI OpenAI Compatible API (Simplified)",
    description="A simplified RESTful API that wraps the gemini-cli tool using -p parameter.",
    version="0.2.0",
)

# Global Gemini CLI instance
gemini_cli: SimplifiedGeminiCLI = None

async def dump_debug_info(filename: str, data: dict):
    """保存调试信息到JSON文件"""
    if not DEBUG_DUMP_ENABLED:
        return
    
    filepath = os.path.join(DEBUG_DUMP_DIR, filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

@app.on_event("startup")
async def startup_event():
    global gemini_cli
    print("🚀 Starting Simplified Gemini CLI API server...")
    print(f"🔧 CLI path: {GEMINI_CLI_PATH}")
    print(f"🐛 Debug dumps: {'enabled' if DEBUG_DUMP_ENABLED else 'disabled'}")
    
    try:
        # 创建简化版 CLI 实例
        gemini_cli = SimplifiedGeminiCLI(cli_path=GEMINI_CLI_PATH)
        
        # 测试连接
        model_info = await gemini_cli.get_model_info()
        if model_info["available"]:
            print(f"✅ Gemini CLI available! Default model: {model_info['default_model']}")
        else:
            print(f"⚠️ Gemini CLI test failed: {model_info.get('error', 'Unknown error')}")
        
        print("🌐 Server ready to handle requests!")
        
    except Exception as e:
        print(f"❌ Failed to initialize Gemini CLI: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to start application: {e}"
        )

@app.on_event("shutdown")
async def shutdown_event():
    print("🛑 Shutting down Simplified Gemini CLI API server...")
    print("👋 Server stopped.")

async def generate_stream_response(request: ChatCompletionRequest, debug_dump_data: dict):
    """生成流式响应"""
    request_id = debug_dump_data["request_id"]
    
    # 合并所有用户消息
    full_prompt = "\n".join([msg.content for msg in request.messages if msg.role == "user"])
    
    # 获取模型（如果指定）
    model = "gemini-2.5-pro" if request.model == "gemini-cli" else request.model
    
    print(f"🔄 Executing streaming prompt for request {request_id}")
    
    try:
        # 流式执行
        async for chunk in gemini_cli.execute_prompt_stream(full_prompt, model=model, timeout=120):
            if chunk.strip():
                # 创建响应消息
                response_message = ChatMessage(role="assistant", content=chunk)
                choice = Choice(index=0, message=response_message, finish_reason=None)
                response = ChatCompletionResponse(
                    id=f"chatcmpl-{request_id}",
                    created=int(time.time()),
                    model=request.model,
                    choices=[choice],
                    usage=None  # 流式响应中不包含usage
                )
                
                yield f"data: {json.dumps(response.dict(exclude_unset=True))}\n\n"
                
                # 记录调试信息
                debug_dump_data["cli_interactions"].append({
                    "type": "stream_chunk",
                    "content": chunk,
                    "timestamp": datetime.datetime.now().isoformat()
                })
        
        # 发送最终响应
        final_usage = Usage(
            prompt_tokens=gemini_cli.estimate_tokens(full_prompt),
            completion_tokens=0,  # 流式模式下难以准确计算
            total_tokens=0
        )
        
        final_choice = Choice(
            index=0, 
            message=ChatMessage(role="assistant", content=""), 
            finish_reason="stop"
        )
        
        final_response = ChatCompletionResponse(
            id=f"chatcmpl-{request_id}",
            created=int(time.time()),
            model=request.model,
            choices=[final_choice],
            usage=final_usage
        )
        
        yield f"data: {json.dumps(final_response.dict(exclude_unset=True))}\n\n"
        yield "data: [DONE]\n\n"
        
        # 保存调试信息
        debug_dump_data["final_response"] = final_response.dict(exclude_unset=True)
        await dump_debug_info(f"{request_id}_stream.json", debug_dump_data)
        
    except Exception as e:
        print(f"❌ Stream error: {e}")
        error_response = {
            "error": {
                "message": str(e),
                "type": "internal_error",
                "code": "gemini_cli_error"
            }
        }
        yield f"data: {json.dumps(error_response)}\n\n"
        yield "data: [DONE]\n\n"
        
        debug_dump_data["error"] = str(e)
        await dump_debug_info(f"{request_id}_error.json", debug_dump_data)

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """处理聊天完成请求"""
    request_id = str(uuid.uuid4())
    debug_dump_data = {
        "request_id": request_id,
        "timestamp_start": datetime.datetime.now().isoformat(),
        "request_body": request.dict(),
        "cli_interactions": []
    }
    
    print(f"📨 Processing request {request_id}, stream: {request.stream}")
    
    try:
        # 检查 Gemini CLI 是否可用
        if not gemini_cli:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Gemini CLI service not available"
            )
        
        # 合并所有用户消息
        full_prompt = "\n".join([msg.content for msg in request.messages if msg.role == "user"])
        
        if not full_prompt.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No user message found in request"
            )
        
        # 获取模型（如果指定）
        model = "gemini-2.5-pro" if request.model == "gemini-cli" else request.model
        
        # 流式响应
        if request.stream:
            return StreamingResponse(
                generate_stream_response(request, debug_dump_data),
                media_type="text/event-stream"
            )
        
        # 非流式响应
        print(f"🔄 Executing non-streaming prompt for request {request_id}")
        
        start_time = time.time()
        response_content = await gemini_cli.execute_prompt(
            full_prompt, 
            model=model, 
            timeout=120
        )
        execution_time = time.time() - start_time
        
        print(f"✅ Got response in {execution_time:.2f}s, length: {len(response_content)} chars")
        
        # 记录调试信息
        debug_dump_data["cli_interactions"].append({
            "type": "complete_response",
            "prompt": full_prompt,
            "response": response_content,
            "execution_time": execution_time,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        # 估算token使用量
        prompt_tokens = gemini_cli.estimate_tokens(full_prompt)
        completion_tokens = gemini_cli.estimate_tokens(response_content)
        total_tokens = prompt_tokens + completion_tokens
        
        # 创建响应
        response_message = ChatMessage(role="assistant", content=response_content)
        choice = Choice(index=0, message=response_message, finish_reason="stop")
        usage = Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens
        )
        
        response = ChatCompletionResponse(
            id=f"chatcmpl-{request_id}",
            created=int(time.time()),
            model=request.model,
            choices=[choice],
            usage=usage
        )
        
        # 保存调试信息
        debug_dump_data["final_response"] = response.dict()
        await dump_debug_info(f"{request_id}_success.json", debug_dump_data)
        
        return response
        
    except Exception as e:
        print(f"❌ Request {request_id} failed: {e}")
        
        # 保存错误信息
        debug_dump_data["error"] = str(e)
        debug_dump_data["timestamp_error"] = datetime.datetime.now().isoformat()
        await dump_debug_info(f"{request_id}_error.json", debug_dump_data)
        
        # 根据错误类型返回适当的HTTP状态码
        if isinstance(e, TimeoutError):
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Request timed out: {str(e)}"
            )
        elif "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Gemini CLI not available: {str(e)}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal error: {str(e)}"
            )

@app.get("/v1/models")
async def list_models():
    """列出可用模型"""
    try:
        model_info = await gemini_cli.get_model_info()
        
        models = [
            {
                "id": "gemini-cli",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "google",
            },
            {
                "id": model_info["default_model"],
                "object": "model", 
                "created": int(time.time()),
                "owned_by": "google",
            }
        ]
        
        return {"object": "list", "data": models}
        
    except Exception as e:
        print(f"❌ Failed to get model info: {e}")
        # 返回默认模型列表
        return {
            "object": "list", 
            "data": [
                {
                    "id": "gemini-cli",
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "google",
                }
            ]
        }

@app.get("/health")
async def health_check():
    """健康检查端点"""
    try:
        model_info = await gemini_cli.get_model_info()
        return {
            "status": "healthy" if model_info["available"] else "degraded",
            "gemini_cli": model_info,
            "timestamp": datetime.datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.datetime.now().isoformat()
        }

# 如果直接运行此文件
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 