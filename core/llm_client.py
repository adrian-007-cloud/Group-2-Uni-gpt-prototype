# This file is the only place that talks to the language model (Ollama).
import requests

LLM_MODEL = "llama3.2"
OLLAMA_URL = "http://localhost:11434/api/chat"


# Send a list of messages to the local model and return its reply text
def ask_model(messages):
    body = {
        "model": LLM_MODEL,
        "stream": False,
        "messages": messages,
        "options": {"temperature": 0.1, "num_predict": 200},   # low value = more consistent answers
    }
    reply = requests.post(OLLAMA_URL, json=body, timeout=300)
    reply.raise_for_status()               # stops with an error if Ollama failed
    return reply.json()["message"]["content"]