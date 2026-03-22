# 🚀 Selenium's Masterpiece: AI Scraper & MCPs

A high-performance, stealthy AI orchestration engine that bridges the gap between local tools and web-based LLMs.

## ✨ Core Components

### 1. `ai_scraper.py`
The powerhouse engine that manages an automated, persistent browser session with dedicated tabs for:
- **ChatGPT**
- **DeepSeek**
- **Perplexity**

It exposes a unified **FastAPI** server (Port 8000) with OpenAI-compatible endpoints, allowing you to route queries to any of these models via simple API calls.

### 2. MCP Servers
Dedicated Model Context Protocol (MCP) servers that allow any compatible client to communicate with the scraper tools:
- `chatgpt_mcp.py` ➔ provides `ask_chatgpt`
- `deepseek_mcp.py` ➔ provides `ask_deepseek`
- `perplexity_mcp.py` ➔ provides `ask_perplexity`

---

## 🚀 How to Use

### 1. Launch the Engine
First, start the main scraper to initialize the browser environment:
```bash
python3 Selenium/ai_scraper.py
```

### 2. Configure MCP Clients
Add the following executable paths to your MCP client configuration (e.g., `mcp_config.json`):

**ChatGPT:**
```bash
python3 /home/mohit/Side-Projects/Selenium/chatgpt_mcp.py
```

**DeepSeek:**
```bash
python3 /home/mohit/Side-Projects/Selenium/deepseek_mcp.py
```

**Perplexity:**
```bash
python3 /home/mohit/Side-Projects/Selenium/perplexity_mcp.py
```

---
*Clean. Fast. Anonymous.*
