import chromadb
from chromadb.utils import embedding_functions

# ── 1. Client persistant (stocke sur disque automatiquement) ─────────
client = chromadb.PersistentClient(path="./ma_base_vecto")

# ── 2. Modèle d'embedding ─────────────────────────────────────────────
ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# ── 3. Créer (ou charger) une collection ─────────────────────────────
collection = client.get_or_create_collection(
    name="mes_documents",
    embedding_function=ef
)

# ── 4. Ajouter des documents ──────────────────────────────────────────
docs = [
    "Python est un langage de programmation puissant",
    "Flask est un micro-framework web léger",
    "Django est un framework web Python complet",
    "FAISS est une bibliothèque de recherche vectorielle",
]

collection.add(
    documents=docs,
    ids=["doc1", "doc2", "doc3", "doc4"],
    metadatas=[{"source": "cours"}] * len(docs)  # métadonnées optionnelles
)

# ── 5. Recherche ──────────────────────────────────────────────────────
results = collection.query(
    query_texts=["framework web Python"],
    n_results=2
)

print("Résultats ChromaDB :")
for doc, dist in zip(results["documents"][0], results["distances"][0]):
    print(f"  {dist:.3f} → {doc}")