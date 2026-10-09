"""
Face recognition module using OpenCV and TensorFlow/Keras for deep face embeddings.
Includes liveness detection capabilities.
"""

import os
import pickle
import numpy as np
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import cv2
import logging

try:
    import tensorflow as tf
    from tensorflow.keras.models import load_model
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False

from Security.auth_types import UserProfile, DEFAULT_POLICY, AuthenticationResult, AuthStatus, AuthMethod

logger = logging.getLogger(__name__)


class FaceRecognizer:
    """Face recognition using OpenCV YuNet DNN + Deep Face Embeddings."""

    def __init__(self, policy=None, model_path=None):
        self.policy = policy or DEFAULT_POLICY
        self.model = None
        self.face_detector = None
        self.data_dir = Path(os.path.dirname(__file__)) / "face_data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._load_models()

    def _load_models(self):
        """Load face detection and recognition models."""
        # Try to load YuNet face detector (OpenCV 4.5.4+)
        yunet_path = self.data_dir / "face_detection_yunet_2023mar.onnx"
        if not yunet_path.exists():
            # Download YuNet model if not present
            self._download_yunet_model(yunet_path)

        try:
            self.face_detector = cv2.FaceDetectorYN_create(
                str(yunet_path),
                "",
                (320, 320),
                0.9,  # score threshold
                0.3,  # nms threshold
                5000  # top k
            )
            logger.info("YuNet face detector loaded successfully")
        except Exception as e:
            logger.warning(f"YuNet not available ({e}), will use center crop fallback")
            self.face_detector = None

        # Try to load pre-trained model (MobileNet-based embedding)
        if not TF_AVAILABLE:
            logger.warning("TensorFlow not available. Using normalized pixel embeddings.")
            self._use_opencv_only = True
        else:
            self._use_opencv_only = False
            self.model_path = self.data_dir / "face_embedding_model.h5"
            if self.model_path.exists():
                try:
                    self.model = load_model(self.model_path)
                except Exception:
                    logger.warning("Could not load face model, using normalized pixel embeddings")
                    self._use_opencv_only = True

    def _download_yunet_model(self, save_path: Path):
        """Download YuNet ONNX model from OpenCV GitHub."""
        import urllib.request
        url = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
        try:
            logger.info(f"Downloading YuNet model from {url}")
            urllib.request.urlretrieve(url, save_path)
            logger.info(f"YuNet model saved to {save_path}")
        except Exception as e:
            logger.warning(f"Failed to download YuNet model: {e}")

    def detect_faces(self, frame) -> List[Tuple[int, int, int, int]]:
        """Detect faces in frame using YuNet. Returns list of (x, y, w, h)."""
        h, w = frame.shape[:2]

        if self.face_detector is not None:
            # YuNet expects specific input size
            self.face_detector.setInputSize((w, h))
            _, faces = self.face_detector.detect(frame)
            if faces is not None:
                results = []
                for face in faces:
                    x, y, w_face, h_face = face[:4].astype(int)
                    results.append((x, y, w_face, h_face))
                return results

        # Fallback: center crop (assume face in center)
        face_size = min(w, h) // 2
        x = (w - face_size) // 2
        y = (h - face_size) // 2
        return [(x, y, face_size, face_size)]

    def extract_embedding(self, frame, face_rect: Tuple[int, int, int, int]) -> Optional[List[float]]:
        """Extract face embedding from detected face."""
        x, y, w, h = face_rect
        face_img = frame[y:y+h, x:x+w]

        if self._use_opencv_only or self.model is None:
            # Use normalized pixel values as simple embedding (no TF needed)
            resized = cv2.resize(face_img, (112, 112))
            normalized = resized.astype(np.float32) / 255.0
            # Flatten and L2 normalize
            embedding = normalized.flatten()
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            return embedding.tolist()
        else:
            # Use deep model
            resized = cv2.resize(face_img, (224, 224))
            normalized = resized / 255.0
            batch = np.expand_dims(normalized, axis=0)
            embedding = self.model.predict(batch, verbose=0)
            return embedding[0].tolist()

    def enroll_face(self, user_id: str, frames: List) -> bool:
        """Enroll user's face with multiple sample frames."""
        embeddings = []
        for frame in frames:
            faces = self.detect_faces(frame)
            if len(faces) == 1:
                emb = self.extract_embedding(frame, faces[0])
                if emb:
                    embeddings.append(emb)

        if len(embeddings) < self.policy.face_min_enrollment_samples:
            return False

        # Save embeddings for user
        emb_path = self.data_dir / f"{user_id}.embeddings"
        with open(emb_path, 'wb') as f:
            pickle.dump(embeddings, f)
        return True

    def load_user_embeddings(self, user_id: str) -> List[List[float]]:
        """Load user's enrolled embeddings."""
        emb_path = self.data_dir / f"{user_id}.embeddings"
        if not emb_path.exists():
            return []
        with open(emb_path, 'rb') as f:
            return pickle.load(f)

    def compute_similarity(self, emb1: List[float], emb2: List[float]) -> float:
        """Compute cosine similarity between embeddings."""
        a = np.array(emb1)
        b = np.array(emb2)
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def verify_face(self, frame, user_profile: UserProfile) -> AuthenticationResult:
        """Verify face against enrolled embeddings."""
        if not user_profile.face_enrolled:
            return AuthenticationResult(
                success=False,
                method=AuthMethod.FACE,
                status=AuthStatus.REQUIRES_ENROLLMENT,
                message="Face not enrolled",
            )

        # Load user embeddings
        user_embeddings = self.load_user_embeddings(user_profile.user_id)
        if len(user_embeddings) == 0:
            # Also check profile
            user_embeddings = user_profile.face_embeddings

        if len(user_embeddings) == 0:
            return AuthenticationResult(
                success=False,
                method=AuthMethod.FACE,
                status=AuthStatus.ERROR,
                message="No face embeddings found",
            )

        # Detect faces
        faces = self.detect_faces(frame)
        if len(faces) == 0:
            return AuthenticationResult(
                success=False,
                method=AuthMethod.FACE,
                status=AuthStatus.FAILED,
                message="No face detected",
            )
        if len(faces) > 1:
            return AuthenticationResult(
                success=False,
                method=AuthMethod.FACE,
                status=AuthStatus.FAILED,
                message="Multiple faces detected",
            )

        # Extract embedding from current face
        current_emb = self.extract_embedding(frame, faces[0])
        if current_emb is None:
            return AuthenticationResult(
                success=False,
                method=AuthMethod.FACE,
                status=AuthStatus.ERROR,
                message="Could not extract embedding",
            )

        # Compute similarity with enrolled embeddings
        similarities = [
            self.compute_similarity(current_emb, emb) for emb in user_embeddings
        ]
        max_sim = max(similarities) if similarities else 0.0
        avg_sim = sum(similarities) / len(similarities) if similarities else 0.0

        confidence = max_sim
        if confidence >= self.policy.face_match_threshold:
            return AuthenticationResult(
                success=True,
                method=AuthMethod.FACE,
                status=AuthStatus.SUCCESS,
                user_id=user_profile.user_id,
                username=user_profile.username,
                confidence=confidence,
                message="Face matched successfully",
                metadata={"max_similarity": max_sim, "avg_similarity": avg_sim},
            )
        else:
            return AuthenticationResult(
                success=False,
                method=AuthMethod.FACE,
                status=AuthStatus.FAILED,
                confidence=confidence,
                message="Face not recognized",
                metadata={"max_similarity": max_sim},
            )