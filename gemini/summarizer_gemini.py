#!/usr/bin/env python3
"""
Mayra Summarizer — Gemini 2.5 Flash
Creates chain-linked summaries every 150 seconds.
"""

import aiohttp
import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("Asia/Kolkata")
MODEL = "gemini-2.5-flash"
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"
MAX_ENTRIES = 200
INTERVAL = 150

def now():
    return datetime.now(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S")

def read_jsonl(p):
    if not p.exists(): return []
    out=[]
    with p.open("r",encoding="utf-8") as f:
        for l in f:
            l=l.strip()
            if not l: continue
            try: out.append(json.loads(l))
            except: pass
    return out

def append_jsonl(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("a",encoding="utf-8") as f:
        f.write(json.dumps(obj,ensure_ascii=False)+"\n")

def overwrite_jsonl(p,arr):
    with p.open("w",encoding="utf-8") as f:
        for x in arr:
            f.write(json.dumps(x,ensure_ascii=False)+"\n")

def enforce_limit(p):
    data = read_jsonl(p)
    if len(data)<=MAX_ENTRIES: return
    overwrite_jsonl(p,data[-MAX_ENTRIES:])

def build_prompt(chats,mem):
    prev = ""
    if mem:
        prev = "Memory context:\n" + "\n".join(f"- {m.get('summary','')}" for m in mem[-10:]) + "\n\n"
    lines=[]
    for c in chats:
        who = "User" if c["role"]=="user" else "Mayra"
        lines.append(f"{who}: {c['content']}")
    system = ("You are a professional summarizer. keep in mind that our main of summarisation is giving local ai memory, these summaries will be used as entry in a jsonl file."
              " Aim for around 60 words. "
              "if chats contain any command then in memory clearly write how it got used during conversation."
              "Be concise, factual, and coherent.")
    return [
        {"role":"system","content":system},
        {"role":"user","content":prev+"Conversation:\n"+"\n".join(lines)}
    ]

async def call_gemini(msgs,key):
    body={"contents":[{"parts":[{"text":m["content"]}]} for m in msgs]}
    url=f"{ENDPOINT}/{MODEL}:generateContent?key={key}"
    async with aiohttp.ClientSession() as s:
        try:
            async with s.post(url,json=body,timeout=120) as r:
                data=await r.json()
                out=[]
                def walk(o):
                    if isinstance(o,dict):
                        if "text" in o: out.append(o["text"])
                        for v in o.values(): walk(v)
                    elif isinstance(o,list):
                        for i in o: walk(i)
                walk(data)
                return " ".join(out).strip()
        except Exception as e:
            return f"[Summarizer error: {e}]"

async def loop(raw,memory,state,key,interval):
    #print(f"🧩 Summarizer active (interval={interval}s)")
    last=0
    while True:
        chats=read_jsonl(raw)
        mem=read_jsonl(memory)
        if len(chats)>last:
            new=chats[last:]
            prompt=build_prompt(new,mem)
            summary=await call_gemini(prompt,key)
            entry={"timestamp":now(),"from_index":last,"to_index":len(chats),"summary":summary}
            append_jsonl(memory,entry)
            enforce_limit(memory)
            print(f"📝 Summary saved ({last}→{len(chats)}): {summary[:80]}...")
            last=len(chats)
        await asyncio.sleep(interval)

def parse():
    p=argparse.ArgumentParser()
    p.add_argument("--session_dir",required=True)
    p.add_argument("--raw_file",required=True)
    p.add_argument("--memory_file",required=True)
    p.add_argument("--state_file",required=True)
    p.add_argument("--interval",default=150,type=int)
    return p.parse_args()

def main():
    a=parse()
    key=os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_SUMMARIZER_KEY")
    if not key:
        print("❌ No API key found.")
        sys.exit(1)
    asyncio.run(loop(Path(a.raw_file),Path(a.memory_file),Path(a.state_file),key,a.interval))

if __name__=="__main__":
    main()
