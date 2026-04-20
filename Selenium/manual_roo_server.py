import time
import json
import uvicorn
import os
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🚀 Define both file paths
REPLY_FILE_1 = "/home/mohit/Side-Projects/Selenium/notes.txt"
REPLY_FILE_2 = "/home/mohit/Side-Projects/Selenium/notes2.txt"
LOG_FILE = "/home/mohit/Side-Projects/Selenium/cline_logs.jsonl"

# 🧠 Global counter track karne ke liye ki kitni requests aayi hain
request_count = 0

def log_to_file(data_type, data):
    """Log data to JSONL file for later analysis"""
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "type": data_type,
                "data": data
            }
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print(f"⚠️ Failed to write to log file: {e}")

@app.post("/v1/chat/completions")
async def openai_chat_completions(request: Request):
    # Global variable ko access karo
    global request_count
    request_count += 1
    
    # 🔄 Logic for file switching
    if request_count == 1:
        current_reply_file = REPLY_FILE_1
        print(f"🥇 First request detected! Using: {current_reply_file}")
    else:
        current_reply_file = REPLY_FILE_2
        print(f"🔁 Request #{request_count} detected! Switched to: {current_reply_file}")

    raw_body = await request.body()
    req_data = json.loads(raw_body)
    
    log_to_file("request", req_data)
    
    print("\n" + "🎀" * 25)
    print("📥 INCOMING REQUEST FROM CLINE (OPENAI MODE):")
    print(f"Model: {req_data.get('model')}")
    print(f"Stream: {req_data.get('stream', False)}")
    print("🎀" * 25 + "\n")

    # 🛑 Check if the dynamically selected file exists
    if not os.path.exists(current_reply_file):
        raise HTTPException(status_code=404, detail=f"File not found: {current_reply_file}")
        
    try:
        with open(current_reply_file, "r", encoding="utf-8") as f:
            file_content = f.read().strip()
            
        # Try to parse as JSON first
        try:
            mock_response = json.loads(file_content)
            is_json = True
            print("📦 Valid JSON detected in file. Using exact response structure.")
        except json.JSONDecodeError:
            # Plain text fallback
            mock_response = None
            is_json = False
            print("📝 Plain text detected.")

        response_id = f"chatcmpl-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        if req_data.get("stream", False):
            async def generate():
                if is_json and mock_response:
                    # ✅ FIXED: Use the EXACT JSON from the selected notes file
                    # Just update the ID and timestamp
                    chunk = mock_response.copy()
                    chunk["id"] = response_id
                    chunk["created"] = int(time.time())
                    
                    log_to_file("response", chunk)
                    
                    print("\n" + "📤" * 30)
                    print("🚀 FULL RAW RESPONSE SENT TO CLINE:")
                    print("📤" * 30)
                    print(json.dumps(chunk, indent=2))
                    print("📤" * 30 + "\n")
                    
                    yield f"data: {json.dumps(chunk)}\n\n"
                    
                    # Send final chunk
                    final_chunk = {
                        "id": response_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": req_data.get("model", "chatgpt-scraper"),
                        "choices": [{
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }]
                    }
                    yield f"data: {json.dumps(final_chunk)}\n\n"
                    yield "data: [DONE]\n\n"
                else:
                    # Plain text streaming fallback
                    reply_text = file_content
                    full_response = ""
                    chunk_size = 8
                    
                    for i in range(0, len(reply_text), chunk_size):
                        text_part = reply_text[i:i+chunk_size]
                        full_response += text_part
                        chunk = {
                            "id": response_id,
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": req_data.get("model", "chatgpt-scraper"),
                            "choices": [{
                                "index": 0,
                                "delta": {"content": text_part},
                                "finish_reason": None
                            }]
                        }
                        yield f"data: {json.dumps(chunk)}\n\n"
                        await asyncio.sleep(0.02)
                    
                    final_chunk = {
                        "id": response_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": req_data.get("model", "chatgpt-scraper"),
                        "choices": [{
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }]
                    }
                    yield f"data: {json.dumps(final_chunk)}\n\n"
                    yield "data: [DONE]\n\n"
                    
                    log_to_file("response_stream", {
                        "model": req_data.get("model"),
                        "message": {"role": "assistant", "content": full_response}
                    })
                    
                    print("\n" + "📤" * 30)
                    print("🚀 FULL RAW RESPONSE SENT (TEXT MODE):")
                    print("📤" * 30)
                    print(full_response)
                    print("📤" * 30 + "\n")
                
            return StreamingResponse(generate(), media_type="text/event-stream")

        else:
            # Non-streaming response
            if is_json and mock_response:
                response_data = mock_response.copy()
                response_data["id"] = response_id
                response_data["created"] = int(time.time())
                response_data["object"] = "chat.completion"
            else:
                response_data = {
                    "id": response_id,
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": req_data.get("model", "chatgpt-scraper"),
                    "choices": [{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": file_content
                        },
                        "finish_reason": "stop"
                    }]
                }
            
            log_to_file("response", response_data)
            
            print("\n" + "📤" * 30)
            print("🚀 FULL RAW RESPONSE SENT (NON-STREAMING):")
            print("📤" * 30)
            print(json.dumps(response_data, indent=2))
            print("📤" * 30 + "\n")
            
            return response_data

    except Exception as e:
        error_log = {"error": str(e), "request": req_data}
        log_to_file("error", error_log)
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("🌸 Manual Roo Server (OpenAI Compatible Mode) is up!")
    print("📊 Full response logging ENABLED")
    print(f"📁 Log files: {REPLY_FILE_1} (1st req) & {REPLY_FILE_2} (subsequent reqs)")
    uvicorn.run("manual_roo_server:app", host="0.0.0.0", port=8000, reload=False)