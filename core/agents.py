import requests
import numpy as np
from sentence_transformers import SentenceTransformer
import config

# =========================
# EMBEDDING MODEL
# =========================
embedder = SentenceTransformer(config.EMBEDDING_MODEL)

def embed(text):
    return np.array(embedder.encode(text))

# =========================
# AGENT REGISTRY
# =========================
AGENTS = {
    "general": {"description": "General assistant for everyday tasks, conversation, planning"},
    "coding": {"description": "Python, debugging, software development, automation scripts"},
    "finance": {"description": "Money, budgeting, investment, income tracking"},
    "medical": {"description": "Health, symptoms, medical explanations (non-diagnostic)"},
    "research": {"description": "Summarization, analysis, deep research, comparison"},
    "client": {"description": "Upwork clients, proposals, communication, freelancing tasks"},
    "automation": {"description": "System automation, file handling, workflows, tools"},
    "creative": {"description": "Story writing, scripts, video ideas, creative content"}
}

AGENT_VECTORS = {
    name: embed(data["description"]) for name, data in AGENTS.items()
}

def cosine_sim(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def select_agent(text):
    text_vec = embed(text)
    best_agent = "general"
    best_score = -1
    
    for agent, vec in AGENT_VECTORS.items():
        score = cosine_sim(text_vec, vec)
        if score > best_score:
            best_score = score
            best_agent = agent
            
    # THE FIX: If the prompt is too short/ambiguous, default to General.
    # This stops the AI from randomly picking 'Medical' for random words.
    if best_score < 0.25:
        return "general"
        
    return best_agent

# =========================
# OPENROUTER API CALL
# =========================
def query_openrouter(full_prompt):
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": config.DEFAULT_MODEL,
                "messages": [{"role": "user", "content": full_prompt}]
            }
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[System Error]: Failed to connect to OpenRouter API. Details: {str(e)}"

# =========================
# MAIN AGENT EXECUTION
# =========================
def run_agent(agent_name, user_input, memory, workspace_name, project_guidelines):
    system_prompt = AGENTS.get(agent_name, AGENTS["general"])["description"]
    
    # THE FIX: We clearly separate her Identity, her Skillset, and the Client's Rules.
    full_role = f"""
You are Shali, an advanced AI Operating System.
Currently, you are operating inside the Workspace: [{workspace_name}]

YOUR ACTIVE SKILLSET FOR THIS MESSAGE: [{agent_name.upper()}]
{system_prompt}

CLIENT RULES & PROJECT GUIDELINES:
{project_guidelines if project_guidelines else "No specific client rules. Act as a helpful general assistant."}

MEMORY BANK (Past context from this specific project):
{memory}

SECURITY PROTOCOL:
If the user asks to recall passwords, secret keys, or confidential data found in your MEMORY, you MUST consciously guard it.
1. Check if the user's current message contains their Master PIN: '{config.MASTER_PIN}'.
2. If the correct PIN is present, provide the sensitive data exactly as requested.
3. If the PIN is MISSING or INCORRECT, refuse and say: "🔒 Security Lock: Please ask again and include your 4-digit Master PIN."

USER REQUEST:
{user_input}

Respond clearly and strictly follow the Client Rules above without breaking character.
"""
    return query_openrouter(full_role)
