# /services/scan_service.py

import cv2
import numpy as np
from inference_sdk import InferenceHTTPClient
from typing import Dict, Any


class ScanError(Exception):
    """Exception dasar untuk error pemindaian."""
    pass


class ScanService:
    def __init__(self, api_url: str, api_key: str, model_id: str):
        """Inisialisasi service dengan konfigurasi Roboflow."""
        self.model_id = model_id
        self.client = InferenceHTTPClient(api_url=api_url, api_key=api_key)

    @staticmethod
    def _order_points(pts: np.ndarray) -> np.ndarray:
        """Mengurutkan 4 titik sudut: tl, tr, br, bl."""
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        return rect

    def process_image(self, image_bytes: bytes) -> bytes:
        """
        Menerima data byte gambar, memindai, dan mengembalikan data byte gambar bersih.
        """
        try:
            image_np = np.frombuffer(image_bytes, np.uint8)
            original_image = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
            
            result = self.client.infer(original_image, model_id=self.model_id)

            if not result or not result.get('predictions'):
                raise ScanError("Deteksi Gagal: Model Roboflow tidak mengembalikan prediksi.")

            # 2. Ekstrak koordinat poligon
            prediction = result['predictions'][0]
            points = prediction['points']
            contour_points = np.array([[p['x'], p['y']] for p in points], dtype=np.int32)

            # 3. Lakukan Transformasi
            # Ubah bytes gambar menjadi format OpenCV
            image_np = np.frombuffer(image_bytes, np.uint8)
            original_image = cv2.imdecode(image_np, cv2.IMREAD_COLOR)

            rect = cv2.minAreaRect(contour_points)
            box = cv2.boxPoints(rect)
            box = np.intp(box)

            ordered_pts = self._order_points(box)
            (tl, tr, br, bl) = ordered_pts

            width_a = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
            width_b = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
            max_width = max(int(width_a), int(width_b))

            height_a = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
            height_b = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
            max_height = max(int(height_a), int(height_b))

            dst = np.array([[0, 0], [max_width - 1, 0], [max_width - 1, max_height - 1], [0, max_height - 1]],
                           dtype="float32")

            m = cv2.getPerspectiveTransform(ordered_pts, dst)
            warped = cv2.warpPerspective(original_image, m, (max_width, max_height))

            # 4. Kembalikan hasil dalam format byte
            _, img_encoded = cv2.imencode('.jpg', warped)
            return img_encoded.tobytes()

        except Exception as e:
            # Tangkap semua error dan bungkus dalam ScanError
            raise ScanError(f"Terjadi error saat pemrosesan gambar: {e}")