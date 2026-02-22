from deepface import DeepFace
import os


class FaceRecognizer:
    def __init__(self, db_path="db/faces", model_name="VGG-Face", detector_backend="mtcnn"):
        self.db_path = db_path
        self.model_name = model_name
        self.detector_backend = detector_backend

        if not os.path.exists(self.db_path):
            os.makedirs(self.db_path)

    def find_identity(self, img_array, threshold=0.4):
        """
        Uses DeepFace.find to search for a face in the database directory.
        img_array: numpy RGB array of the cropped face.
        Returns (name: str, distance: float)
        """
        try:
            results = DeepFace.find(
                img_path=img_array,
                db_path=self.db_path,
                model_name=self.model_name,
                detector_backend=self.detector_backend,
                enforce_detection=False,
                silent=True,
            )

            if results and len(results) > 0 and not results[0].empty:
                df = results[0]
                match = df.iloc[0]
                identity_path = match["identity"]
                identity_name = os.path.basename(os.path.dirname(identity_path))

                distance_col = None
                for col in df.columns:
                    if any(m in col for m in ["cosine", "euclidean", "distance"]):
                        distance_col = col
                        break

                if distance_col:
                    distance = float(match[distance_col])
                    if distance <= threshold:
                        return identity_name, distance

            return "Unknown", 1.0
        except Exception as e:
            print(f"Error during DeepFace.find: {e}")
            return "Unknown", 1.0
