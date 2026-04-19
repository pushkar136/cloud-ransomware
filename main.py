from fastapi import FastAPI, WebSocket, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import logging
from typing import List
import os

app = FastAPI(title="Ransomware Cloud CC Project")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow local agents to POST to this backend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Basic in-memory store for connected websocket clients (Dashboards)
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        # Convert dict to JSON string
        msg_str = json.dumps(message)
        for connection in self.active_connections:
            try:
                await connection.send_text(msg_str)
            except Exception as e:
                logger.error(f"Error sending to websocket: {e}")

manager = ConnectionManager()


# Ensure frontend directory exists
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend_dashboard")
app.mount("/static", StaticFiles(directory=frontend_path, html=True), name="static")


class AgentAlert(BaseModel):
    machine_id: str
    filename: str
    entropy: float
    event_type: str
    timestamp: float
    risk_level: str

@app.get("/")
async def get():
    # Serve index.html
    index_path = os.path.join(frontend_path, "index.html")
    with open(index_path, "r") as f:
        content = f.read()
    return HTMLResponse(content)

@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # We don't expect the dashboard to send much, mostly listen
            # but we need to keep connection open
            data = await websocket.receive_text()
    except Exception as e:
        manager.disconnect(websocket)

@app.post("/api/alerts")
async def receive_alert(alert: AgentAlert):
    logger.info(f"Received alert from agent: {alert}")
    
    # Analyze across agents could happen here
    # For now, just broadcast directly to UI
    await manager.broadcast(alert.dict())
    
    return {"status": "Alert received and broadcasted"}

if __name__ == "__main__":
    import uvicorn
    # Make sure this runs properly
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
