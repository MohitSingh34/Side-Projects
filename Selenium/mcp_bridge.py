import asyncio
import requests
import json
import os
import subprocess
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, CallToolResult

app = Server("ai-scraper-mcp-cluster")
import asyncio
from collections import deque

# Global registry to track live workers and their rolling logs! 🧠
worker_registry = {}
@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="list_active_agents",
            description="Get a list of all currently active AI agents (browser tabs) available in the swarm.",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="ask_ai_agent",
            description="Delegate a task, question, OR SEND A FILE/IMAGE to a specific AI agent running in a browser tab.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "The ID of the agent (e.g., 'chatgpt', 'gemini')"
                    },
                    "prompt": {
                        "type": "string",
                        "description": "The detailed task or question for the agent"
                    },
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "OPTIONAL. A list of local file paths (like screenshots) to send to the agent alongside the prompt."
                    }
                },
                "required": ["agent_id", "prompt"]
            }
        ),
        Tool(
            name="launch_ai_agent",
            description="Spawn a new browser tab for a new AI agent (ChatGPT, DeepSeek, or Gemini) to handle more parallel tasks.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_type": {
                        "type": "string",
                        "description": "The type of agent to launch: strictly 'chatgpt', 'deepseek', or 'gemini'"
                    }
                },
                "required": ["agent_type"]
            }
        ),
        Tool(
            name="list_system_windows",
            description="Get a list of all visible application windows currently open on the Xubuntu system. Useful to find the exact title for taking screenshots.",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="take_system_screenshot",
            description="Take a screenshot of a specific open window by its title. Returns the local file path to the saved screenshot image.",
            inputSchema={
                "type": "object",
                "properties": {
                    "window_title": {
                        "type": "string",
                        "description": "The exact title of the window to capture (can be found using list_system_windows)."
                    }
                },
                "required": ["window_title"]
            }
        ),
        Tool(
            name="close_system_window",
            description="Closes/kills a specific application window on the system. Pass the full ID string obtained from list_system_windows.",
            inputSchema={
                "type": "object",
                "properties": {
                    "window_id": {
                        "type": "string",
                        "description": "The exact full ID string of the window to close (e.g., '0x0520000c (latitude mcp_bridge.py — Kate)')"
                    }
                },
                "required": ["window_id"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:
    if name == "list_active_agents":
        try:
            res = requests.get("http://localhost:8000/v1/models", timeout=10)
            data = res.json()
            agents = [model["id"] for model in data.get("data", [])]
            return CallToolResult(content=[TextContent(type="text", text=f"Available agents for delegation: {json.dumps(agents)}")])
        except Exception as e:
            return CallToolResult(content=[TextContent(type="text", text=f"Error connecting to Swarm: {e}")])

    elif name == "ask_ai_agent":
        agent_id = arguments.get("agent_id")
        prompt = arguments.get("prompt")
        files = arguments.get("files", [])
        try:
            res = requests.post(
                "http://localhost:8000/v1/agent_chat",
                json={"agent": agent_id, "prompt": prompt, "files": files},
                timeout=300
            )
            data = res.json()
            if "error" in data:
                return CallToolResult(content=[TextContent(type="text", text=f"Swarm Error: {data['error']}")], isError=True)
            response_text = data.get("response", str(data))
            return CallToolResult(content=[TextContent(type="text", text=response_text)])
        except Exception as e:
            return CallToolResult(content=[TextContent(type="text", text=f"Error talking to {agent_id}: {e}")], isError=True)

    elif name == "launch_ai_agent":
        agent_type = arguments.get("agent_type")
        try:
            res = requests.post(
                "http://localhost:8000/v1/launch_agent",
                json={"agent_type": agent_type},
                timeout=30
            )
            data = res.json()
            if "error" in data:
                return CallToolResult(content=[TextContent(type="text", text=f"Spawn Error: {data['error']}")], isError=True)
            return CallToolResult(content=[TextContent(type="text", text=f"{data['message']} Available agents now: {json.dumps(data['available_agents'])}")])
        except Exception as e:
            return CallToolResult(content=[TextContent(type="text", text=f"Error launching agent: {e}")], isError=True)

    elif name == "list_system_windows":
        try:
            res = requests.get("http://localhost:8761/v1/system/windows", timeout=10)
            return CallToolResult(content=[TextContent(type="text", text=json.dumps(res.json(), indent=2))])
        except Exception as e:
            return CallToolResult(content=[TextContent(type="text", text=f"System API Error: {e}")], isError=True)

    elif name == "take_system_screenshot":
        title = arguments.get("window_title")
        safe_title = title.replace(" ", "_").replace("/", "_")
        local_path = f"/tmp/mcp_screenshot_{safe_title}.png"
        try:
            res = requests.get(f"http://localhost:8761/v1/system/screenshot/{title}", timeout=15)
            if res.status_code == 200:
                with open(local_path, "wb") as f:
                    f.write(res.content)
                return CallToolResult(content=[TextContent(type="text", text=f"Screenshot taken successfully! Image saved locally at: {local_path}")])
            else:
                return CallToolResult(content=[TextContent(type="text", text=f"Screenshot failed: {res.text}")], isError=True)
        except Exception as e:
            return CallToolResult(content=[TextContent(type="text", text=f"System API Error: {e}")], isError=True)

    elif name == "close_system_window":
        window_id = arguments.get("window_id")
        try:
            res = requests.post(
                "http://localhost:8761/v1/system/window/close",
                json={"window_id": window_id},
                timeout=10
            )
            data = res.json()
            if res.status_code == 200:
                return CallToolResult(content=[TextContent(type="text", text=data["message"])])
            else:
                return CallToolResult(content=[TextContent(type="text", text=f"Error closing window: {data}")], isError=True)
        except Exception as e:
            return CallToolResult(content=[TextContent(type="text", text=f"System API Error: {e}")], isError=True)

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
