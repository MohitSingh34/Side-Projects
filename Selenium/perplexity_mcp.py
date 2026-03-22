import sys
import json
import urllib.request
import time
import emoji

# Configuration - Combined scraper port 8000 pe chal raha hai
API_URL = "http://localhost:8000/v1/chat/completions"

def log(msg):
    sys.stderr.write(f"[perplexity-mcp] {msg}\n")
    sys.stderr.flush()

def read_message():
    line = sys.stdin.readline()
    if not line:
        return None
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None

def write_message(msg):
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()

def handle_chat_tool(arguments):
    prompt = arguments.get("prompt", "")
    files = arguments.get("files", [])
    if not prompt:
        return {"content": [{"type": "text", "text": "Error: Prompt is required."}], "isError": True}

    # Demojize prompt to prevent BMP errors in down-stream Selenium ChromeDriver
    safe_prompt = emoji.demojize(prompt)

    payload = {
        "model": "perplexity-scraper",
        "messages": [{"role": "user", "content": safe_prompt}],
        "files": files,
        "temperature": 0.7
    }

    req = urllib.request.Request(
        API_URL, 
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        log(f"Waiting 1s before calling scraper for prompt: {prompt[:20]}...")
        time.sleep(1)
        
        log("Sending request to Perplexity scraper...")
        with urllib.request.urlopen(req, timeout=300) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            content = res_data["choices"][0]["message"]["content"]
            return {"content": [{"type": "text", "text": content}]}
            
    except urllib.error.HTTPError as e:
        try:
            error_body = e.read().decode("utf-8")
        except:
            error_body = str(e)
        log(f"HTTP Error {e.code}: {error_body}")
        return {"content": [{"type": "text", "text": f"Scraper returned HTTP {e.code}: {error_body}"}], "isError": True}
        
    except Exception as e:
        log(f"Error calling API: {e}")
        return {"content": [{"type": "text", "text": f"Error communicating with Perplexity Scraper: {e}"}], "isError": True}

def main():
    log("Server started")
    while True:
        msg = read_message()
        if msg is None:
            break

        msg_id = msg.get("id")
        method = msg.get("method")

        if method == "initialize":
            write_message({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {
                            "listChanged": False
                        }
                    },
                    "serverInfo": {
                        "name": "perplexity-scraper-mcp",
                        "version": "1.0.0"
                    }
                }
            })
        elif method == "notifications/initialized":
            continue
        elif method == "tools/list":
            write_message({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": [{
                        "name": "ask_perplexity",
                        "description": "Send a prompt to Perplexity via the local scraper proxy.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "prompt": {
                                    "type": "string",
                                    "description": "The message to send to Perplexity."
                                },
                                "files": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Optional list of absolute paths to files to upload."
                                }
                            },
                            "required": ["prompt"]
                        }
                    }]
                }
            })
        elif method == "tools/call":
            params = msg.get("params", {})
            name = params.get("name")
            args = params.get("arguments", {})

            if name == "ask_perplexity":
                result = handle_chat_tool(args)
                write_message({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": result
                })
            else:
                write_message({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32601,
                        "message": f"Tool not found: {name}"
                    }
                })
        else:
            if msg_id is not None:
                write_message({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                })

if __name__ == "__main__":
    main()
