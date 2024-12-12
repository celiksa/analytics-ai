from fastapi import FastAPI, WebSocket, WebSocketDisconnect,Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from psql_agent import DbAgent
import base64
from typing import List, Dict
import uvicorn
import asyncpg
from pydantic import BaseModel

app = FastAPI()

chat_histories: Dict[str, List[dict]] = {}

class ChatSession(BaseModel):
    session_id: str
    messages: List[dict]

@app.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str):
    """Get chat history for a specific session."""
    return chat_histories.get(session_id, [])

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database agent
db_agent = DbAgent(viz_dir="./visualizations")

@app.on_event("startup")
async def startup_event():
    await db_agent.setup('postgresql://postgres:postgres@localhost:54320/employees')

@app.on_event("shutdown")
async def shutdown_event():
    await db_agent.close()


@app.get("/databases")
async def list_databases():
    """List all available PostgreSQL databases and their schemas."""
    try:
        # Connect to postgres database to list all databases
        conn = await asyncpg.connect(
            'postgresql://postgres:postgres@localhost:54320/postgres'
        )
        
        # Get all databases
        databases = await conn.fetch("""
            SELECT datname 
            FROM pg_database 
            WHERE datistemplate = false AND datname != 'postgres'
        """)
        
        # For each database, get its schemas
        result = []
        for db in databases:
            db_name = db['datname']
            # Connect to specific database to get schemas
            db_conn = await asyncpg.connect(
                f'postgresql://postgres:postgres@localhost:54320/{db_name}'
            )
            schemas = await db_conn.fetch("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
            """)
            await db_conn.close()
            
            result.append({
                "name": db_name,
                "schemas": [s['schema_name'] for s in schemas]
            })
            
        await conn.close()
        return result
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to list databases: {str(e)}"}
        )


@app.websocket("/ws/chat")
async def websocket_endpoint(
    websocket: WebSocket,
    db: str = None,
    schema: str = None,
    session_id: str = Query(...)
    ):

    if not db or not schema:
        await websocket.close(code=1008, reason="Database and schema must be specified")
        return
    
    await websocket.accept()
    try:
        db_agent = DbAgent(viz_dir="./visualizations")
        await db_agent.setup(
            f'postgresql://postgres:postgres@localhost:54320/{db}',
            schema=schema
        )

        # Get existing chat history
        existing_messages = chat_histories.get(session_id, [])

        while True:
            try:
                
                # Receive message from client
                message = await websocket.receive_text()
                
                # Execute query without streaming
                try:
                    result = await db_agent.query(message, db, schema, message_history=existing_messages)
                    # Update history with new messages
                    new_messages = result.new_messages()
                    existing_messages.extend(new_messages)
                    chat_histories[session_id] = existing_messages
                    
                    # Send the main response
                    await websocket.send_json({
                        "type": "message",
                        "content": result.data.message,
                        "status": "complete"
                    })
                    
                    # Send visualization if available
                    if result.data.has_visualization and db_agent.viz_handler.current_visualization:
                        await websocket.send_json({
                            "type": "visualization",
                            "content": base64.b64encode(db_agent.viz_handler.current_visualization).decode('utf-8')
                        })
                    
                except Exception as e:
                    error_message = f"Error processing query: {str(e)}"
                    await websocket.send_json({
                        "type": "error",
                        "content": error_message
                    })
                
                # Always send end marker
                await websocket.send_json({"type": "end"})
                
            except WebSocketDisconnect:
                print("Client disconnected")
                break
            except Exception as e:
                print(f"Error in websocket loop: {str(e)}")
                await websocket.send_json({
                    "type": "error",
                    "content": f"Error: {str(e)}"
                })
                await websocket.send_json({"type": "end"})
                
    except Exception as e:
        print(f"Fatal websocket error: {str(e)}")
        try:
            await websocket.close()
        except:
            pass

@app.post("/api/chat")
async def chat(message: dict):
    try:
        result = await db_agent.query(message["content"])
        
        # Convert visualization to base64 if available
        viz_data = None
        if result.data.has_visualization and db_agent.viz_handler.current_visualization:
            viz_data = base64.b64encode(db_agent.viz_handler.current_visualization).decode('utf-8')
        
        return JSONResponse({
            "query": result.data.query,
            "results": result.data.results,
            "message": result.data.message,
            "visualization": viz_data
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )
    


if __name__ == "__main__":
    uvicorn.run(
        "api:app", 
        host="0.0.0.0", 
        port=8001, 
        reload=True,
        ws='websockets'  # Explicitly specify websockets
    )