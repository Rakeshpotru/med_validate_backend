# import json
# import uvicorn
# from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect
# from fastapi.middleware.cors import CORSMiddleware
# import socket
# import logging
# from typing import Dict

# router = APIRouter()

# # Logging and IP detection
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# hostname = socket.gethostname()
# local_ip = socket.gethostbyname(hostname)
# logger.info(f"Detected Local IP: {local_ip}")

# # Document data - Initialize as empty, to be replaced by client
# json_data = {}

# # WebSocket client management
# client_states: Dict[WebSocket, Dict] = {}

# @router.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     client_states[websocket] = {"cursor": None}
#     logger.info(f"Connected clients: {list(client_states.keys())}")

#     try:
#         while True:
#             raw_data = await websocket.receive_text()
#             logger.info(f"Received WebSocket message: {raw_data}")
#             data = json.loads(raw_data)

#             # Replace entire json_data with incoming content
#             new_content = data.get("content")
#             if new_content:
#                 global json_data
#                 json_data = new_content  # Overwrite entire json_data
#                 logger.info("Document replaced with new content")

#             broadcast_data = {
#                 "type": "content_update",
#                 "content": json_data,
#                 "client_id": data.get("client_id"),
#                 "cursor": data.get("cursor")
#             }

#             # Broadcast to all other clients
#             for client in client_states:
#                 if client != websocket:
#                     await client.send_text(json.dumps(broadcast_data))
#                     logger.info(f"Broadcasted to client: {client}")
#     except WebSocketDisconnect:
#         del client_states[websocket]
#         logger.info(f"Client disconnected, remaining: {list(client_states.keys())}")
#     except Exception as e:
#         logger.error(f"WebSocket error: {e}")
#         del client_states[websocket]

# @router.get("/health")
# async def health_check():
#     """Health check endpoint"""
#     return {
#         "status": "healthy",
#         "connected_clients": len(client_states),
#         "server_ip": local_ip
#     }

# if __name__ == "__main__":
#     # Run the application on port 8009, binding to all interfaces
#     uvicorn.run("main:app",
#                 host="0.0.0.0",
#                 port=8009,
#                 reload=True,
#                 log_level="info")


from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import logging
from typing import Set, Dict

router = APIRouter()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory storage for WebSocket connections per task_id
rooms: Dict[str, Set[WebSocket]] = {}

@router.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    await websocket.accept()
    if task_id not in rooms:
        rooms[task_id] = set()
    rooms[task_id].add(websocket)
    logger.info(f"Client connected to task room: {task_id}, total clients: {len(rooms[task_id])}")

    try:
        while True:
            raw_data = await websocket.receive_text()
            logger.info(f"Received message for task {task_id}: {raw_data}")
            try:
                data = json.loads(raw_data)
                if data.get("type") == "content_update":
                    # Broadcast to all clients in the same task_id room, excluding sender
                    broadcast_data = {
                        "type": "content_update",
                        "content": data.get("content"),
                        "client_id": data.get("client_id"),
                        "username": data.get("username"),
                        "cursor": data.get("cursor"),
                        "formState": data.get("formState")
                    }
                    for client in rooms.get(task_id, []):
                        if client != websocket:
                            await client.send_json(broadcast_data)
                            logger.info(f"Broadcasted to client in task room {task_id}")
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received for task {task_id}: {raw_data}")
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
    except WebSocketDisconnect:
        rooms[task_id].remove(websocket)
        logger.info(f"Client disconnected from task room {task_id}, remaining: {len(rooms[task_id])}")
        if not rooms[task_id]:
            del rooms[task_id]
    except Exception as e:
        logger.error(f"WebSocket error for task {task_id}: {e}")
        rooms[task_id].remove(websocket)
        if not rooms[task_id]:
            del rooms[task_id]