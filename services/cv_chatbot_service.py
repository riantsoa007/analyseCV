import json
from typing import List

from models import CV
from services.chroma_cv_store import ChromaCVStore


class CVChatbotService:
    # ... (garder _build_ollama_error inchangé)

    @staticmethod
    def _get_relevant_chunks(question: str, chroma_path: str, chroma_collection: str, top_k: int = 10) -> List[dict]:
        """Récupère des chunks texte directement depuis Chroma, pas les CV entiers."""
        from services.chroma_cv_store import ChromaCVStore  # si non importé
        try:
            collection = ChromaCVStore._get_collection(chroma_path, chroma_collection)
            results = collection.query(
                query_texts=[question],
                n_results=top_k
            )
            chunks = []
            if results and results.get("documents") and results.get("metadatas"):
                documents = results["documents"][0] if results["documents"] else []
                metadatas = results["metadatas"][0] if results["metadatas"] else []
                for doc, meta in zip(documents, metadatas):
                    text = str(doc) if doc is not None else ""
                    meta_dict = meta if isinstance(meta, dict) else {}
                    chunks.append({
                        "cv_id": meta_dict.get("cv_id", "inconnu"),
                        "file_name": meta_dict.get("file_name", "inconnu"),
                        "text": text
                    })
            return chunks
        except Exception:
            return []

    @staticmethod
    def _build_context_from_chunks(chunks: List[dict], max_tokens: int = 3000) -> str:
        """Construit un contexte texte à partir des chunks bruts."""
        if not chunks:
            return "Aucun extrait de CV disponible."

        context_parts = []
        total_chars = 0
        max_chars = max_tokens * 4  # approximation
      
        for chunk in chunks:
            if not isinstance(chunk, dict):
                continue
            cv_id = chunk.get("cv_id", "inconnu")
            file_name = chunk.get("file_name", "inconnu")
            text = chunk.get("text", "")
            
            text_str = str(text) if text is not None else ""
            if not text_str.strip():
                continue

            header = f"[CV {cv_id} - {file_name}]\n"
            chunk_text = header + text_str + "\n"
            if total_chars + len(chunk_text) > max_chars:
                # on coupe le dernier chunk si nécessaire
                remaining = max_chars - total_chars
                if remaining > 100:
                    context_parts.append(chunk_text[:remaining])
                break
            context_parts.append(chunk_text)
            total_chars += len(chunk_text)

        return "\n".join(context_parts) if context_parts else "Aucun extrait de CV disponible."

    @staticmethod
    def answer(question, history, ollama_model, chroma_path, chroma_collection, ollama_host):
        try:
            from ollama import Client
        except ImportError as exc:
            raise RuntimeError("Le package ollama n'est pas installe.") from exc

        # 1. Récupérer les chunks pertinents (pas les CV entiers)
        
        chunks = CVChatbotService._get_relevant_chunks(
            question, chroma_path, chroma_collection, top_k=10
        )

        # 2. Construire le contexte texte brut
        context = CVChatbotService._build_context_from_chunks(chunks, max_tokens=3500)
        print(context)

        # 3. Messages système
        messages = [
            {
                "role": "system",
                "content": (
                    "Tu es un assistant RH. Tu réponds uniquement à partir des extraits de CV ci-dessous. "
                    "Sois concis et cite les CV par leur ID ou nom de fichier. "
                    "Si l'information n'est pas dans les extraits, dis-le clairement."
                ),
            },
            {"role": "system", "content": f"Extraits de CV :\n{context}"},
        ]

        # Historique limité à 4 échanges
        for item in history[-4:]:
            messages.append({"role": item["role"], "content": item["content"]})

        messages.append({"role": "user", "content": question})

        client = Client(host=ollama_host)
        try:
            response = client.chat(
                model=ollama_model,
                messages=messages,
                options={"num_ctx": 4096, "temperature": 0.2}
            )
        except Exception as exc:
            raise RuntimeError(
                CVChatbotService._build_ollama_error(exc, ollama_host, ollama_model)
            ) from exc

        # Pour l'affichage, on remonte les CV parents (optionnel)
        cv_ids = list({chunk["cv_id"] for chunk in chunks if chunk["cv_id"]})
        candidate_cvs = CV.query.filter(CV.id.in_(cv_ids)).all() if cv_ids else []

        return {
            "answer": response["message"]["content"],
            "candidate_cvs": candidate_cvs,
        }