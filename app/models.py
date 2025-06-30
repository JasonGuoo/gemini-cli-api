from pydantic import BaseModel, Field
from typing import List, Optional

class ChatMessage(BaseModel):
    """A message in a chat conversation."""
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    """Request model for the chat completions endpoint."""
    model: str
    messages: List[ChatMessage]
    stream: Optional[bool] = False

class Choice(BaseModel):
    """A choice in a chat completion response."""
    index: int
    message: ChatMessage
    finish_reason: str

class Usage(BaseModel):
    """Token usage statistics for a chat completion."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class ChatCompletionResponse(BaseModel):
    """Response model for the chat completions endpoint."""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Choice]
    usage: Usage
