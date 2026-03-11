import os
import pickle
import numpy as np
from deepface import DeepFace


class FaceRecognizer:
    """
    Face recognizer with an in-memory embedding cache.

    We pre-compute embeddings for every registered identity at startup and compare
    new face crops against the cache using cosine distance.  This brings per-face
    recognition cost from ~500 ms down to ~5 ms.
    """

    def __init__(self, db_path=None, model_name="VGG-Face"):
        self.db_path = db_path
        self.model_name = model_name
        # Each entry: {"name": str, "embedding": np.ndarray, "path": str}
        self._cache: list[dict] = []

        if self.db_path and not os.path.exists(self.db_path):
            os.makedirs(self.db_path)

        if self.db_path:
            self.load_cache()

    @property
    def _cache_file(self):
        return os.path.join(self.db_path, "embeddings_cache.pkl") if self.db_path else None

    # ── Public API ───────────────────────────────────────────────

    def load_cache(self):
        """
        Loads embeddings from the file cache if it exists and is up to date.
        Otherwise, rebuilds the database by calling reload_db().
        """
        cache_file = self._cache_file

        if not cache_file or not os.path.exists(cache_file):
            print("[recognizer] No cache file found. Building cache...")
            self.reload_db()
            return

        # Check if database has been modified since cache was created
        cache_mtime = os.path.getmtime(cache_file)
        needs_reload = False

        for root, _, files in os.walk(self.db_path):
            if os.path.getmtime(root) > cache_mtime:
                needs_reload = True
                break
            for file in files:
                if self._is_image(file):
                    file_path = os.path.join(root, file)
                    if os.path.getmtime(file_path) > cache_mtime:
                        needs_reload = True
                        break
            if needs_reload:
                break

        if needs_reload:
            print("[recognizer] Database modified. Rebuilding cache...")
            self.reload_db()
        else:
            try:
                assert cache_file is not None
                with open(cache_file, "rb") as f:
                    self._cache = pickle.load(f)
                print(f"[recognizer] Loaded {len(self._cache)} embeddings from file cache.")
            except Exception as e:
                print(f"[recognizer] Error loading cache file: {e}. Rebuilding...")
                self.reload_db()

    def reload_db(self):
        """
        (Re)build the in-memory embedding cache from the images stored in
        ``self.db_path``.  Call this after adding or deleting identities.
        """
        cache: list[dict] = []
        if not os.path.exists(self.db_path):
            self._cache = cache
            return

        for person_name in sorted(os.listdir(self.db_path)):
            person_dir = os.path.join(self.db_path, person_name)
            if not os.path.isdir(person_dir):
                continue
            for img_file in os.listdir(person_dir):
                img_path = os.path.join(person_dir, img_file)
                if not self._is_image(img_path):
                    continue
                try:
                    reps = DeepFace.represent(
                        img_path=img_path,
                        model_name=self.model_name,
                        detector_backend="mtcnn",  # DB images are full photos, need detection
                        enforce_detection=False,
                    )
                    if reps:
                        emb = np.array(reps[0]["embedding"], dtype=np.float32)
                        cache.append(
                            {"name": person_name, "embedding": emb, "path": img_path}
                        )
                except Exception as e:
                    print(f"[recognizer] skip {img_path}: {e}")

        self._cache = cache
        cache_file = self._cache_file
        if cache_file:
            try:
                with open(cache_file, "wb") as f:
                    pickle.dump(self._cache, f)
                print(f"[recognizer] Cache saved to {cache_file}")
            except Exception as e:
                print(f"[recognizer] Failed to save cache file: {e}")

        print(f"[recognizer] Cache loaded: {len(cache)} embeddings for "
              f"{len(set(c['name'] for c in cache))} identities")

    def find_identity(self, face_crop: np.ndarray, threshold: float = 0.20):
        """
        Compute the embedding for *face_crop* (an RGB numpy array that already
        contains a detected face) and compare against the cached database
        embeddings using cosine distance.

        Returns ``(name, distance)`` where *distance* ≤ *threshold* means match.
        Threshold is cosine distance (0 = identical, 1 = orthogonal).
        """
        if not self._cache:
            return "Unknown", 1.0

        try:
            reps = DeepFace.represent(
                img_path=face_crop,
                model_name=self.model_name,
                detector_backend="skip",  # face already cropped by MTCNN
                enforce_detection=False,
            )
            if not reps:
                return "Unknown", 1.0

            query_emb = np.array(reps[0]["embedding"], dtype=np.float32)
        except Exception as e:
            print(f"[recognizer] Error computing embedding: {e}")
            return "Unknown", 1.0

        # Vectorised cosine distance against all cached embeddings
        db_matrix = np.stack([c["embedding"] for c in self._cache])  # (M, D)
        distances = self._cosine_distances(query_emb, db_matrix)     # (M,)

        best_idx = int(np.argmin(distances))
        best_dist = float(distances[best_idx])

        #print(best_dist, threshold, best_dist <= threshold)
        
        if best_dist <= threshold:
            return self._cache[best_idx]["name"], best_dist
        return "Unknown", best_dist

    # ── Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _cosine_distances(query: np.ndarray, matrix: np.ndarray) -> np.ndarray:
        """Return cosine distances between *query* (1‑D) and each row of *matrix*."""
        query_norm = query / (np.linalg.norm(query) + 1e-10)
        matrix_norms = matrix / (np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-10)
        similarities = matrix_norms @ query_norm  # (M,)
        return 1.0 - similarities

    @staticmethod
    def _is_image(path: str) -> bool:
        return path.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".webp"))
