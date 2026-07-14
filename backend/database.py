import os
import sqlite3
import numpy as np

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evaluator.db")

def get_connection():
    """Returns a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            source_dataset TEXT NOT NULL,
            embedding BLOB NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def save_documents(docs: list[dict]):
    """
    Saves a list of documents to the database.
    Each doc should be: {"text": str, "source_dataset": str, "embedding": list[float]}
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    insert_data = []
    for doc in docs:
        emb_bytes = np.array(doc["embedding"], dtype=np.float32).tobytes()
        insert_data.append((doc["text"], doc["source_dataset"], emb_bytes))
        
    cursor.executemany("""
        INSERT INTO documents (text, source_dataset, embedding)
        VALUES (?, ?, ?)
    """, insert_data)
    
    conn.commit()
    conn.close()

def retrieve_top_k(query_embedding: list[float], k: int = 3, dataset_filter: str = None) -> list[dict]:
    """
    Retrieves the top k matches using cosine similarity in NumPy.
    Optional filter by source_dataset (e.g. 'squad' or 'truthfulqa').
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    if dataset_filter:
        cursor.execute("SELECT id, text, source_dataset, embedding FROM documents WHERE source_dataset = ?", (dataset_filter,))
    else:
        cursor.execute("SELECT id, text, source_dataset, embedding FROM documents")
        
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return []
        
    doc_ids = []
    texts = []
    datasets = []
    embeddings = []
    
    for row in rows:
        doc_ids.append(row["id"])
        texts.append(row["text"])
        datasets.append(row["source_dataset"])
        # Unpack embedding from blob
        emb = np.frombuffer(row["embedding"], dtype=np.float32)
        embeddings.append(emb)
        
    # Convert query embedding and db embeddings to numpy arrays
    q_emb = np.array(query_embedding, dtype=np.float32)
    db_embs = np.array(embeddings, dtype=np.float32) # Shape: (N, 384)
    
    # Compute Cosine Similarity: dot(A, B) / (norm(A) * norm(B))
    dot_products = np.dot(db_embs, q_emb)
    db_norms = np.linalg.norm(db_embs, axis=1)
    q_norm = np.linalg.norm(q_emb)
    
    # Avoid division by zero
    norms = db_norms * q_norm
    norms[norms == 0] = 1e-10
    
    scores = dot_products / norms
    
    # Get top k indices sorted in descending order
    top_indices = np.argsort(scores)[::-1][:k]
    
    results = []
    for idx in top_indices:
        results.append({
            "id": int(doc_ids[idx]),
            "text": str(texts[idx]),
            "source_dataset": str(datasets[idx]),
            "score": float(scores[idx])
        })
        
    return results

def get_stats() -> dict:
    """Returns database statistics."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT source_dataset, COUNT(*) as count FROM documents GROUP BY source_dataset")
    rows = cursor.fetchall()
    conn.close()
    
    stats = {row["source_dataset"]: row["count"] for row in rows}
    stats["total"] = sum(stats.values())
    return stats
