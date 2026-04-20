import asyncio
import requests
import json
import psutil
import subprocess
import os
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, CallToolResult

app = Server("ai-worker-mcp")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="talk_to_worker",
            description="Send a task or prompt directly to a spawned worker's port and wait for its completion response.",
            inputSchema={
                "type": "object",
                "properties": {
                    "port": {"type": "integer", "description": "Port number of the worker (e.g., 8005)"},
                    "prompt": {"type": "string", "description": "The explicit task, instructions, or question for the worker"},
                    "files": {"type": "array", "items": {"type": "string"}, "description": "Optional: List of absolute file paths to send to the worker"}
                },
                "required": ["port", "prompt"]
            }
        ),
        Tool(
            name="get_worker_status",
            description="Check the operating system to see if a worker is actively running on a specific port, and fetch its latest logs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "port": {"type": "integer", "description": "Port number of the worker to check (e.g., 8005)"}
                },
                "required": ["port"]
            }
        ),
        Tool(
            name="kill_worker_agent",
            description="Safely terminate the worker process running on a specific port.",
            inputSchema={
                "type": "object",
                "properties": {
                    "port": {"type": "integer", "description": "Port number of the worker to kill (e.g., 8005)"}
                },
                "required": ["port"]
            }
        ),
        Tool(
            name="spawn_worker_agent",
            description="Launch a new worker agent process in the background with its own port and Chrome profile.",
            inputSchema={
                "type": "object",
                "properties": {
                    "worker_name": {"type": "string", "description": "Unique ID for the agent, e.g. worker-deepseek-1"},
                    "model": {"type": "string", "description": "Model type: chatgpt, deepseek, or gemini"},
                    "port": {"type": "integer", "description": "Port number, e.g. 8005"},
                    "profile": {"type": "string", "description": "Absolute path to Chrome profile directory"}
                },
                "required": ["worker_name", "model", "port", "profile"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:
    
    if name == "talk_to_worker":
        port = arguments.get("port")
        prompt = arguments.get("prompt")
        files = arguments.get("files", [])
        try:
            res = requests.post(
                f"http://localhost:{port}/v1/chat/completions", 
                json={
                    "model": "worker-node", 
                    "messages": [{"role": "user", "content": prompt}], 
                    "files": files
                }, 
                timeout=600 
            )
            
            if res.status_code == 200:
                data = res.json()
                reply = data.get("choices", [{}])[0].get("message", {}).get("content", "Error: Empty response")
                return CallToolResult(content=[TextContent(type="text", text=f"✅ Worker {port} replied:\n\n{reply}")])
            else:
                return CallToolResult(content=[TextContent(type="text", text=f"❌ Error {res.status_code}: {res.text}")], isError=True)
                
        except requests.exceptions.ConnectionError:
            return CallToolResult(content=[TextContent(type="text", text=f"❌ Connection Error: Is the worker on port {port} actually running?")], isError=True)
        except Exception as e:
            return CallToolResult(content=[TextContent(type="text", text=f"❌ Error talking to worker: {e}")], isError=True)

    elif name == "spawn_worker_agent":
        worker_name = arguments.get("worker_name")
        model = arguments.get("model")
        port = arguments.get("port")

        # Paths
        raw_profile = arguments.get("profile") # e.g., /home/mohit/chrome-profile-v4
        master_clean_profile = "/home/mohit/chrome-worker-master-template"
        target_profile = f"/home/mohit/chrome-worker-{port}"

        # 1. Prevent spawning if port is already taken
        for proc in psutil.process_iter(['pid']):
            try:
                for conn in proc.connections(kind='inet'):
                    if conn.laddr.port == port:
                        return CallToolResult(content=[TextContent(type="text", text=f"⚠️ Port {port} is already in use! Kill it first or choose another port.")], isError=True)
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue

        import shutil

        # 🚀 2. CREATE THE MASTER TEMPLATE (Only happens once!)
        if not os.path.exists(master_clean_profile):
            try:
                # Heavy filtered copy to strip out locks and gigabytes of cache
                shutil.copytree(
                    raw_profile,
                    master_clean_profile,
                    ignore=shutil.ignore_patterns(
                        'SingletonLock', 'SingletonCookie', 'SingletonSocket',
                        'Cache*', 'GPUCache', 'Code Cache', 'Network Persistent State'
                    )
                )
            except Exception as e:
                return CallToolResult(content=[TextContent(type="text", text=f"❌ Failed to create clean master template: {e}")], isError=True)

        # 🚀 3. LIGHTNING FAST WORKER CLONE
        if not os.path.exists(target_profile):
            try:
                # Raw, unfiltered copy from the clean, dormant template
                shutil.copytree(master_clean_profile, target_profile)
            except Exception as e:
                return CallToolResult(content=[TextContent(type="text", text=f"❌ Failed to clone profile for worker: {e}")], isError=True)

        cmd = [
            "/home/mohit/Side-Projects/Selenium/myenv/bin/python3",
            "/home/mohit/Side-Projects/Selenium/ai_scraper_worker.py",
            "--model", model,
            "--port", str(port),
            "--profile", target_profile,  # 👈 Pass the target profile to the worker
            "--worker-name", worker_name
        ]

        try:
            log_file_path = f"/tmp/worker_{port}.log"
            log_file = open(log_file_path, "w", encoding="utf-8")

            custom_env = os.environ.copy()
            if "DISPLAY" not in custom_env:
                custom_env["DISPLAY"] = ":0"
            if "XAUTHORITY" not in custom_env:
                custom_env["XAUTHORITY"] = "/home/mohit/.Xauthority"

            subprocess.Popen(
                cmd,
                cwd="/home/mohit/Side-Projects/Selenium",
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                env=custom_env
            )

            return CallToolResult(content=[TextContent(type="text", text=f"🚀 Successfully spawned '{worker_name}' ({model}) on port {port}. Fast-cloned from master template. Logs routing to {log_file_path}.")])
        except Exception as e:
            return CallToolResult(content=[TextContent(type="text", text=f"❌ Failed to spawn worker: {e}")], isError=True)


    elif name == "get_worker_status":
        port = arguments.get("port")
        worker_proc = None
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                for conn in proc.connections(kind='inet'):
                    if conn.laddr.port == port:
                        worker_proc = proc
                        break
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue
            if worker_proc: break
            
        # Try to read logs to give Cline context
        log_file_path = f"/tmp/worker_{port}.log"
        recent_logs = "\n[No log file found]"
        if os.path.exists(log_file_path):
            try:
                with open(log_file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    recent_logs = "".join(lines[-15:]) # Grab last 15 lines
            except Exception:
                pass
            
        if worker_proc:
            try:
                mem_mb = worker_proc.memory_info().rss / (1024 * 1024)
                return CallToolResult(content=[TextContent(type="text", text=f"✅ Worker is LIVE on port {port}.\nPID: {worker_proc.pid}\nMemory Used: {mem_mb:.1f} MB\n\n📝 Latest Logs:\n{recent_logs}")])
            except Exception:
                return CallToolResult(content=[TextContent(type="text", text=f"✅ Worker is LIVE on port {port} (PID: {worker_proc.pid}).\n\n📝 Latest Logs:\n{recent_logs}")])
        else:
            return CallToolResult(content=[TextContent(type="text", text=f"⚠️ No active worker found on port {port}. Process is dead or offline.\n\n📝 Last known logs:\n{recent_logs}")])

    elif name == "kill_worker_agent":
        port = arguments.get("port")
        killed_pids = []
        
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                for conn in proc.connections(kind='inet'):
                    if conn.laddr.port == port:
                        pid = proc.pid
                        proc.terminate()
                        try:
                            proc.wait(timeout=5)
                        except psutil.TimeoutExpired:
                            proc.kill()
                        killed_pids.append(pid)
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue
                
        if killed_pids:
            return CallToolResult(content=[TextContent(type="text", text=f"💀 Successfully terminated worker on port {port} (PIDs: {killed_pids}).")])
        else:
            return CallToolResult(content=[TextContent(type="text", text=f"ℹ️ Could not find any running worker on port {port} to kill.")])

    raise ValueError(f"Unknown tool: {name}")

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
