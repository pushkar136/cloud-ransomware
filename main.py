from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import logging

app = FastAPI()

# ---------------------------
# Logging setup
# ---------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cloud-backend")

# ---------------------------
# Data Model (Agent Alert)
# ---------------------------
class AgentAlert(BaseModel):
    machine_id: str
    filename: str
    entropy: float
    timestamp: str

# ---------------------------
# WebSocket Connection Manager
# ---------------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("Dashboard connected")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info("Dashboard disconnected")

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

# ---------------------------
# ROOT ROUTE (IMPORTANT FOR RENDER)
# ---------------------------
@app.get("/")
def home():
    return {"status": "Cloud Backend Running 🚀"}

# ---------------------------
# SIMPLE DASHBOARD PAGE (OPTIONAL)
# ---------------------------
@app.get("/dashboard")
def get_dashboard():
    html_content = """
    <html>
        <head>
            <title>Cloud Monitoring</title>
        </head>
        <body>
            <h2>Cloud Ransomware Detection Dashboard</h2>
            <p>WebSocket connected...</p>
            <script>
                const ws = new WebSocket("wss://" + location.host + "/ws/dashboard");
                ws.onmessage = (event) => {
                    console.log("Alert:", event.data);
                };
            </script>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# ---------------------------
# WEBSOCKET FOR DASHBOARD
# ---------------------------
@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ---------------------------
# API ENDPOINT (AGENT → CLOUD)
# ---------------------------
@app.post("/api/alerts")
async def receive_alert(alert: AgentAlert):
    logger.info(f"Received alert: {alert}")
    await manager.broadcast(alert.dict())
    return {"status": "Alert received and broadcasted"}