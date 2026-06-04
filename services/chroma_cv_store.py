import os


class ChromaCVStore:
    @staticmethod
    def _get_collection(vector_db_path, collection_name="cvs"):
        try:
            import chromadb
            from chromadb.utils import embedding_functions
        except ImportError as exc:
            raise RuntimeError("Le package chromadb n'est pas installe.") from exc

        os.makedirs(vector_db_path, exist_ok=True)

        client = chromadb.PersistentClient(path=vector_db_path)
        embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )

        return client.get_or_create_collection(
            name=collection_name,
            embedding_function=embedding_function,
        )

    @staticmethod
    def upsert_cv(vector_db_path, cv, raw_text, collection_name="cvs"):
        collection = ChromaCVStore._get_collection(vector_db_path, collection_name)
        document_id = f"cv_{cv.id}"

        collection.upsert(
            documents=[raw_text],
            ids=[document_id],
            metadatas=[
                {
                    "cv_id": cv.id,
                    "file_name": cv.file_name,
                    "file_path": cv.file_path,
                }
            ],
        )

    @staticmethod
    def delete_cv(vector_db_path, cv_id, collection_name="cvs"):
        collection = ChromaCVStore._get_collection(vector_db_path, collection_name)
        collection.delete(ids=[f"cv_{cv_id}"])

    @staticmethod
    def search_cv_ids(vector_db_path, query_text, collection_name="cvs", limit=5):
        collection = ChromaCVStore._get_collection(vector_db_path, collection_name)
        try:
            results = collection.query(query_texts=[query_text], n_results=limit)
        except Exception:
            return []

        ids = results.get("ids", [[]])
        extracted_ids = []

        for item in ids[0]:
            if item.startswith("cv_"):
                try:
                    extracted_ids.append(int(item.replace("cv_", "", 1)))
                except ValueError:
                    continue

        return extracted_ids
