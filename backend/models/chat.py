"""
Chat and API-related Pydantic models for BuilderSolve Agent
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class ChatMessagePart(BaseModel):
    """Part of a chat message"""
    text: str


class ChatMessageContent(BaseModel):
    """Chat message format for API"""
    role: str  # 'user' | 'model'
    parts: List[ChatMessagePart]


class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    message: str
    history: List[ChatMessageContent] = []
    currentJobId: Optional[str] = None


class ToolExecution(BaseModel):
    """Tool execution record"""
    id: str
    toolName: str
    args: Dict[str, Any]
    result: Any
    timestamp: float


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    text: str
    toolExecutions: List[ToolExecution] = []
    switchedJobId: Optional[str] = None


class ChatMessage(BaseModel):
    """Chat message model (for internal use)"""
    id: str
    role: str  # 'user' | 'model' | 'system'
    content: str
    timestamp: datetime
    isThinking: Optional[bool] = None
    toolExecutions: Optional[List[ToolExecution]] = None