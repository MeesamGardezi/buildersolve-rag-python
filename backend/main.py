"""
FastAPI main application with WebSocket support for real-time chat
"""
import os
import sys
import json
from typing import List, Dict, Any
from datetime import datetime

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from constants import DEFAULT_COMPANY_ID, DEFAULT_JOB_ID
from models.types import ChatRequest, ChatResponse, Job
from services.firebase_service import fetch_job_data, search_jobs
from services.gemini_service import send_message_to_agent

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="BuilderSolve Agent API",
    description="Agentic RAG system for construction project management",
    version="1.0.0"
)

# CORS configuration for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Connection manager for WebSocket
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"✅ WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print(f"❌ WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)


manager = ConnectionManager()


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "BuilderSolve Agent API",
        "version": "1.0.0"
    }


@app.get("/api/job/{job_id}")
async def get_job(job_id: str, company_id: str = DEFAULT_COMPANY_ID):
    """
    REST endpoint to fetch job data
    """
    try:
        job_data = await fetch_job_data(company_id, job_id)
        return JSONResponse(content=job_data)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/jobs/search")
async def search_jobs_endpoint(query: str, company_id: str = DEFAULT_COMPANY_ID):
    """
    REST endpoint to search for jobs
    """
    try:
        results = await search_jobs(query, company_id)
        return JSONResponse(content={"results": results})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """
    REST endpoint for chat (alternative to WebSocket)
    """
    try:
        response = await send_message_to_agent(
            message=request.message,
            history=request.history,
            current_job_id=request.currentJobId or DEFAULT_JOB_ID
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat
    
    Expected message format:
    {
        "type": "message",
        "message": "User message here",
        "history": [...],
        "currentJobId": "job_id_here"
    }
    
    Response format:
    {
        "type": "response",
        "text": "Agent response",
        "toolExecutions": [...],
        "switchedJobId": "new_job_id" (optional)
    }
    """
    await manager.connect(websocket)
    current_job_id = DEFAULT_JOB_ID
    
    try:
        # Send welcome message
        welcome_job = await fetch_job_data(DEFAULT_COMPANY_ID, DEFAULT_JOB_ID)
        await manager.send_personal_message({
            "type": "welcome",
            "job": welcome_job,
            "message": f"Hello! I'm your BuilderSolve agent. I have loaded the context for **{welcome_job.get('projectTitle')}**.\n\nYou can ask me about estimates, milestones, client details, or ask me to perform calculations on the data."
        }, websocket)
        
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            if data.get("type") == "message":
                message = data.get("message", "")
                history = data.get("history", [])
                current_job_id = data.get("currentJobId", current_job_id)
                
                # Send typing indicator
                await manager.send_personal_message({
                    "type": "typing",
                    "isTyping": True
                }, websocket)
                
                # Get response from agent
                response = await send_message_to_agent(
                    message=message,
                    history=history,
                    current_job_id=current_job_id
                )
                
                # Update current job if switched
                if response.switchedJobId:
                    current_job_id = response.switchedJobId
                    # Fetch new job data
                    new_job = await fetch_job_data(DEFAULT_COMPANY_ID, current_job_id)
                    
                    # Send job update
                    await manager.send_personal_message({
                        "type": "job_update",
                        "job": new_job
                    }, websocket)
                
                # Send response
                await manager.send_personal_message({
                    "type": "response",
                    "text": response.text,
                    "toolExecutions": [te.dict() for te in response.toolExecutions],
                    "switchedJobId": response.switchedJobId
                }, websocket)
            
            elif data.get("type") == "ping":
                # Respond to ping to keep connection alive
                await manager.send_personal_message({
                    "type": "pong"
                }, websocket)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"❌ WebSocket Error: {e}")
        try:
            await manager.send_personal_message({
                "type": "error",
                "message": "An error occurred. Please refresh and try again."
            }, websocket)
        except:
            pass
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)