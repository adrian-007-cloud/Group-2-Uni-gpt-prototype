# This file is the only place that talks to the language model (Ollama).
import requests
import json

LLM_MODEL = "llama3.2"
OLLAMA_URL = "http://localhost:11434/api/chat"


# Send a list of messages to the local model and return its reply text
def ask_model(messages, model_name = LLM_MODEL):
    body = {
        "model": model_name,
        "stream": False,
        "messages": messages,
        "keep_alive" : "30m",
        "options": {"temperature": 0.1, "num_predict": 120},   # low value = more consistent answers
    }
    reply = requests.post(OLLAMA_URL, json=body, timeout=300)
    reply.raise_for_status()               # stops with an error if Ollama failed
    return reply.json()["message"]["content"]

def ask_model_stream(messages, model_name=LLM_MODEL):
    body = {
        "model": model_name,
        "stream": True,
        "messages": messages,
        "keep_alive": "30m",
        "options": {"temperature": 0.1, "num_predict": 1000, "num_ctx": 4096},
    }
    reply = requests.post(OLLAMA_URL, json=body, stream=True, timeout=300)
    reply.raise_for_status()
    for line in reply.iter_lines():
        if line:
            chunk = json.loads(line)
            yield chunk["message"]["content"]
            if chunk.get("done"):
                break