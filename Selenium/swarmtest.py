import asyncio
import os
import sys
from collections import deque
import requests

# Global registry exactly like MCP bridge
worker_registry = {}

async def run_swarm_test():
    # Setup variables just like arguments.get()
    agent_id = "test-worker-1"
    model = "chatgpt"
    port = 8005
    profile = "/home/mohit/chrome-profile-worker-test"
    script_path = "/home/mohit/Side-Projects/Selenium/ai_scraper_worker.py"
    
    print(f"🚀 [ORCHESTRATOR] Spawning worker '{agent_id}' on port {port} using asyncio exec...")

    # 👇 YAHAN SE EXACT MCP BRIDGE KA CODE SHURU 👇
    if agent_id in worker_registry and worker_registry[agent_id]["status"] in ["Booting", "Running"]:
        print(f"⚠️ Worker '{agent_id}' is already {worker_registry[agent_id]['status']}.")
        return

    cmd = ["/home/mohit/Side-Projects/Selenium/myenv/bin/python3", script_path, "--model", model, "--port", str(port), "--profile", profile, "--worker-name", agent_id]
    
    try:
        PROJECT_DIR = "/home/mohit/Side-Projects/Selenium"
        # 🚀 Fire up the process
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=PROJECT_DIR  # <--- YEHI MISSING THA! Iske bina path errors aate hain.
        )
        
        # 🧠 Setup memory for this worker
        log_buffer = deque(maxlen=20)
        worker_registry[agent_id] = {
            "process": process, 
            "logs": log_buffer, 
            "status": "Booting" # Initial state
        }

        # 🕵️‍♂️ The Silent Observer: Background task to drain logs and update status
        async def monitor_worker_stream(a_id, proc, buffer):
            # Har worker ke liye ek unique log file banayenge
            log_file_path = f"/tmp/worker_{a_id}.log"
            
            with open(log_file_path, "a", encoding="utf-8") as f:
                while True:
                    line_bytes = await proc.stdout.readline()
                    if not line_bytes:
                        break # Process died or stream closed
                        
                    line = line_bytes.decode('utf-8').strip()
                    buffer.append(line)
                    
                    # Live file mein write karo!
                    f.write(f"{line}\n")
                    f.flush() # Force OS to write to disk immediately
                    
                    # State transitions based on terminal output
                    if "Uvicorn running on" in line:
                        if a_id in worker_registry: worker_registry[a_id]["status"] = "Running"
                    elif "Shutting down gracefully" in line:
                        if a_id in worker_registry: worker_registry[a_id]["status"] = "Shutting Down"
                        
                # Loop broke, process is no longer running
                if a_id in worker_registry:
                    worker_registry[a_id]["status"] = "Dead/Stopped"
                f.write(f"\n--- WORKER {a_id} TERMINATED ---\n")

        # Launch the observer in the background without awaiting it!
        asyncio.create_task(monitor_worker_stream(agent_id, process, log_buffer))

        # ⚡ Return immediately to the Orchestrator
        print(f"🚀 Spawn sequence initiated for '{agent_id}' on port {port}. The process is running in the background. Check logs at /tmp/worker_{agent_id}.log")
            
    except Exception as e:
        print(f"❌ Failed to spawn worker: {e}")
        return
    # 👆 YAHAN TAK EXACT MCP BRIDGE KA CODE HAI 👆


    # --- TEST POLLING LOGIC ---
    print("\n⏳ Polling worker_registry to see if status changes to 'Running' (Max 90s)...")
    is_ready = False
    for _ in range(90):
        await asyncio.sleep(1)
        current_status = worker_registry.get(agent_id, {}).get("status")
        if current_status == "Running":
            is_ready = True
            break
        elif current_status == "Dead/Stopped":
            print("❌ Process died unexpectedly. Check the log file.")
            break

    if not is_ready:
        print(f"❌ Worker failed to bind to port {port}. Final memory logs:\n" + "\n".join(worker_registry[agent_id]["logs"]))
        return

    print(f"\n✅ FULLY ARMED AND OPERATIONAL! Worker status is RUNNING.")
    print("\n=========================================================================")
    print("Ab tum kisi bhi terminal se manual curl command maar ke test kar sakte ho:")
    print(f"""
curl -X POST http://localhost:{port}/v1/chat/completions \\
-H "Content-Type: application/json" \\
-d '{{
  "model": "worker-node",
  "messages": [
    {{"role": "user", "content": "Write a 2 line brutal poem about debugging code in Linux."}}
  ]
}}'
""")
    print("=========================================================================")
    print("🚨 Waiting here... Jab test khatam ho jaye toh press CTRL+C to kill worker.")
    
    try:
        # Keep the script alive so the background task keeps logging
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass


async def main():
    try:
        await run_swarm_test()
    except KeyboardInterrupt:
        print("\n🛑 Test done. User pressed CTRL+C.")
    finally:
        print("\n🧹 Cleaning up... Terminating worker process.")
        if "test-worker-1" in worker_registry:
            proc = worker_registry["test-worker-1"]["process"]
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                proc.kill()
            print("💀 Worker successfully terminated. No zombies left behind!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass # Handle the outer keyboard interrupt gracefully