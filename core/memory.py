import os
import re
import chromadb
from sentence_transformers import SentenceTransformer
import config

print("[MEMORY] Loading SentenceTransformer model...")
embedder = SentenceTransformer(config.EMBEDDING_MODEL)

DB_PATH = os.path.abspath("./data/chroma_db")
os.makedirs(DB_PATH, exist_ok=True)
client = chromadb.PersistentClient(path=DB_PATH)

FEEDBACK_COLLECTION = "feedback_scores"
GLOBAL_COLLECTION = "command_center"

def embed(text):
    return embedder.encode(text).tolist()

def sanitize_db_name(workspace_name):
    """Sanitize workspace name for ChromaDB collection naming"""
    clean = re.sub(r'[^a-z0-9_-]', '_', workspace_name.lower())
    clean = clean.strip('_')
    if len(clean) < 3:
        clean = "db_" + clean
    return clean[:60]

def get_db(workspace_name):
    """Get or create isolated collection for workspace"""
    safe_name = sanitize_db_name(workspace_name)
    return client.get_or_create_collection(safe_name)

def get_feedback_db():
    return client.get_or_create_collection(FEEDBACK_COLLECTION)

def store_memory(memory_data, workspace="command_center"):
    """Store memory with project isolation"""
    # Normalize workspace to project_id
    project_id = sanitize_db_name(workspace)
    db = get_db(project_id)
    
    if isinstance(memory_data, str):
        content = memory_data
        meta = {"type": "general", "project_id": project_id}
    else:
        content = memory_data.get("content", "")
        meta = dict(memory_data)  # Copy to avoid mutation
    
    # CRITICAL: Ensure project_id is always set in metadata
    meta["project_id"] = project_id
    meta["workspace"] = workspace
    
    clean_meta = {k: str(v) for k, v in meta.items()}
    
    db.add(
        documents=[content],
        embeddings=[embed(content)],
        metadatas=[clean_meta],
        ids=[str(hash(content + str(clean_meta)))]
    )
    print(f"[MEMORY SAVED] -> {workspace}")

def store_feedback(query_text, response_text, feedback_type, workspace="Command Center (Global)"):
    db = get_feedback_db()
    score = 1 if feedback_type == "up" else -1
    
    db.add(
        documents=[f"Q:{query_text} A:{response_text}"],
        embeddings=[embed(query_text)],
        metadatas=[{
            "workspace": workspace,
            "feedback": feedback_type,
            "score": str(score),
            "query": query_text[:200],
            "response": response_text[:500]
        }],
        ids=[str(hash(query_text + response_text + feedback_type))]
    )
    print(f"[FEEDBACK SAVED] {feedback_type} for query in {workspace}")

def retrieve_feedback(query_text, workspace="Command Center (Global)", k=5):
    db = get_feedback_db()
    
    try:
        results = db.query(
            query_embeddings=[embed(query_text)],
            n_results=k * 2
        )
        
        feedback_scores = []
        if results["metadatas"] and results["metadatas"][0]:
            for meta in results["metadatas"][0]:
                if meta.get("workspace") == workspace:
                    feedback_scores.append(int(meta.get("score", 0)))
        
        return sum(feedback_scores) if feedback_scores else 0
    except Exception:
        return 0

def retrieve_memory(query, workspace="command_center", k=5):
    """Retrieve memories scoped to specific project only - NO bleeding"""
    # STRICT ISOLATION: Only search within the specified project
    project_id = sanitize_db_name(workspace)
    db = get_db(project_id)
    
    memories = []
    
    results = db.query(
        query_embeddings=[embed(query)],
        n_results=k,
        where={"project_id": project_id}  # Enforce scope at DB level
    )
    
    if results["documents"] and results["documents"][0]:
        for i in range(len(results["documents"][0])):
            mem = {
                "content": results["documents"][0][i], 
                **results["metadatas"][0][i]
            }
            # Double-check scope guard
            if mem.get("project_id") == project_id:
                memories.append(mem)
        
    return memories

def retrieve_thread_memory(query, workspace, thread_id, k=5):
    """Retrieve thread-scoped memories with project isolation"""
    project_id = sanitize_db_name(workspace)
    db = get_db(project_id)
    
    try:
        results = db.query(
            query_embeddings=[embed(query)],
            n_results=k * 2,
            where={"thread_id": thread_id, "project_id": project_id}
        )
    except Exception:
        results = db.query(
            query_embeddings=[embed(query)],
            n_results=k,
            where={"project_id": project_id}
        )
    
    memories = []
    if results["documents"] and results["documents"][0]:
        for i in range(len(results["documents"][0])):
            mem = {
                "content": results["documents"][0][i], 
                **results["metadatas"][0][i]
            }
            # Verify project scope
            if mem.get("project_id") == project_id:
                memories.append(mem)
            
    return memories
