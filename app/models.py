from pydantic import BaseModel, Field
from typing import List, Optional

class ChatMessage(BaseModel):
    """A message in a chat conversation."""
    role: str
    content: str

class Delta(BaseModel):
    """Delta object for streaming responses."""
    content: Optional[str] = None
    role: Optional[str] = None
    reasoning_content: Optional[str] = None

class ChatCompletionRequest(BaseModel):
    """Request model for the chat completions endpoint."""
    model: str
    messages: List[ChatMessage]
    stream: Optional[bool] = False

class Choice(BaseModel):
    """A choice in a chat completion response."""
    index: int
    message: Optional[ChatMessage] = None  # For non-streaming
    delta: Optional[Delta] = None  # For streaming
    finish_reason: Optional[str] = None
    logprobs: Optional[str] = None # Assuming logprobs can be a string for now, or adjust type as needed

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
    usage: Optional[Usage]