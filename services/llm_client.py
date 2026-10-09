import requests
import config

def query_openrouter(system_prompt, user_input, memory_context):
    """Handles the actual HTTP request to the OpenRouter API."""
    
    prompt = f"""
You are an expert AI agent named Shali.

ROLE:
{system_prompt}

MEMORY:
{memory_context}

USER:
{user_input}

Respond clearly and practically.
"""

    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": config.DEFAULT_MODEL,  # Fixed variable name here!
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }
        )
        
        # This catches HTTP errors like invalid API keys or server downtime
        r.raise_for_status() 
        
        data = r.json()
        return data["choices"][0]["message"]["content"]
        
    except Exception as e:
        return f"[System Error]: Failed to connect to OpenRouter API. Details: {str(e)}"
