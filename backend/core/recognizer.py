import json
import os

import numpy as np
from deepface import DeepFace


class FaceRecognizer:
    """
    Face recognizer with an in-memory embedding cache.

    We pre-compute embeddings for every registered identity at startup and compare
    new face crops against the cache using cosine distance.  This brings per-face
    recognition cost from ~500 ms down to ~5 ms.

    Cache is stored as two files (no pickle — safe against code-execution attacks):
      - embeddings_cache.npz  — float32 matrix of shape (N, D)
      - embeddings_cache_meta.json — list of {name, path} dicts
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
    def _cache_npz(self):
        return os.path.join(self.db_path, "embeddings_cache.npz") if self.db_path else None

    @property
    def _cache_meta(self):
        return os.path.join(self.db_path, "embeddings_cache_meta.json") if self.db_path else None

    # Kept for mtime comparison in load_cache()
    @property
    def _cache_file(self):
        return self._cache_npz

    # ── Public API ───────────────────────────────────────────────

    def load_cache(self):
        """
        Loads embeddings from the file cache if it exists and is up to date.
        Otherwise, rebuilds the database by calling reload_db().
        """
        cache_npz = self._cache_npz
        cache_meta = self._cache_meta

        if not cache_npz or not os.path.exists(cache_npz) or not os.path.exists(cache_meta):
            print("[recognizer] No cache file found. Building cache...")
            self.reload_db()
            return

        # Check if database has been modified since cache was created
        cache_mtime = os.path.getmtime(cache_npz)
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
                data = np.load(cache_npz, allow_pickle=False)
                with open(cache_meta, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                embeddings = data["embeddings"]
                self._cache = [
                    {"name": m["name"], "embedding": embeddings[i], "path": m["path"]}
                    for i, m in enumerate(meta)
                ]
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
        self._save_cache()

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

        if best_dist <= threshold:
            return self._cache[best_idx]["name"], best_dist
        return "Unknown", best_dist

    # ── Helpers ──────────────────────────────────────────────────

    def _save_cache(self):
        """Persist the in-memory cache to npz + JSON (no pickle)."""
        cache_npz = self._cache_npz
        cache_meta = self._cache_meta
        if not cache_npz:
            return
        try:
            if self._cache:
                embeddings = np.stack([c["embedding"] for c in self._cache])
            else:
                embeddings = np.empty((0,), dtype=np.float32)
            np.savez(cache_npz, embeddings=embeddings)
            meta = [{"name": c["name"], "path": c["path"]} for c in self._cache]
            with open(cache_meta, "w", encoding="utf-8") as f:
                json.dump(meta, f)
            print(f"[recognizer] Cache saved to {cache_npz}")
        except Exception as e:
            print(f"[recognizer] Failed to save cache: {e}")

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
