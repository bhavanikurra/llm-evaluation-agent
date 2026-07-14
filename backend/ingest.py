import sys
import os
import argparse
from sentence_transformers import SentenceTransformer
from datasets import load_dataset

# Ensure backend folder is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import database

def clean_text(text: str) -> str:
    """Basic text cleanup."""
    if not text:
        return ""
    return " ".join(text.replace("\n", " ").split())

def chunk_text(text: str, max_words: int = 100) -> list[str]:
    """Splits text into chunks of roughly max_words."""
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0
    
    for word in words:
        current_chunk.append(word)
        current_length += 1
        if current_length >= max_words:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_length = 0
            
    if current_chunk:
        chunks.append(" ".join(current_chunk))
        
    return chunks

def ingest_datasets(limit: int = 50):
    """
    Downloads and ingests SQuAD and TruthfulQA datasets,
    chunks paragraphs, computes embeddings, and saves to SQLite.
    """
    print("Initializing Database...")
    database.init_db()
    
    print("Loading SentenceTransformer model ('all-MiniLM-L6-v2')...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    
    docs_to_save = []
    
    # 1. Ingest SQuAD
    print(f"Fetching SQuAD dataset (validation split, limit: {limit})...")
    try:
        squad = load_dataset("squad", split="validation", streaming=True)
        squad_iter = iter(squad)
        
        seen_contexts = set()
        count = 0
        while count < limit:
            try:
                row = next(squad_iter)
            except StopIteration:
                break
                
            context = clean_text(row["context"])
            if context and context not in seen_contexts:
                seen_contexts.add(context)
                # Chunk SQuAD contexts to keep vector search precise
                chunks = chunk_text(context, max_words=80)
                for chunk in chunks:
                    docs_to_save.append({
                        "text": chunk,
                        "source_dataset": "squad"
                    })
                count += 1
        print(f"Successfully processed {count} unique SQuAD contexts into {len(docs_to_save)} chunks.")
    except Exception as e:
        print(f"Error loading SQuAD: {e}. Proceeding with alternative datasets...")
        
    # 2. Ingest TruthfulQA
    print(f"Fetching TruthfulQA dataset (generation split, limit: {limit})...")
    try:
        # TruthfulQA validation split has 'generation' task type
        truthful_qa = load_dataset("truthful_qa", "generation", split="validation", streaming=True)
        tqa_iter = iter(truthful_qa)
        
        tqa_count = 0
        while tqa_count < limit:
            try:
                row = next(tqa_iter)
            except StopIteration:
                break
                
            question = clean_text(row["question"])
            best_answer = clean_text(row["best_answer"])
            
            # Combine QA into a statement block that can be retrieved
            context_str = f"Question: {question} Correct Answer: {best_answer}"
            docs_to_save.append({
                "text": context_str,
                "source_dataset": "truthful_qa"
            })
            tqa_count += 1
        print(f"Successfully processed {tqa_count} TruthfulQA statements.")
    except Exception as e:
        print(f"Error loading TruthfulQA: {e}")
        
    if not docs_to_save:
        print("No documents were loaded. Aborting database save.")
        return
        
    # 3. Compute Embeddings and save
    print(f"Computing embeddings for {len(docs_to_save)} total segments...")
    texts = [doc["text"] for doc in docs_to_save]
    embeddings = model.encode(texts, show_progress_bar=True)
    
    for i, doc in enumerate(docs_to_save):
        doc["embedding"] = embeddings[i].tolist()
        
    print("Saving documents to database...")
    database.save_documents(docs_to_save)
    
    stats = database.get_stats()
    print("Database seeding completed successfully!")
    print(f"Stats: {stats}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest datasets for LLM Eval Knowledge Base")
    parser.add_argument("--limit", type=int, default=50, help="Number of records to ingest from each dataset")
    args = parser.parse_args()
    
    ingest_datasets(limit=args.limit)
