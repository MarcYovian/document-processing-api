import cv2
import base64
import requests
from inference_sdk import InferenceHTTPClient
from PIL import Image
from io import BytesIO

# Inisialisasi Roboflow client
CLIENT = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key="tHovuYfATheJl3ayXOhU"
)

# Fungsi untuk capture frame dari webcam dan konversi ke format yang bisa diproses
def capture_frame():
    cap = cv2.VideoCapture(0)
    print("Tekan 's' untuk capture dan infer")
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Gagal membuka kamera")
            break

        cv2.imshow("Live Feed - Tekan 's' untuk Capture", frame)

        key = cv2.waitKey(1)
        if key == ord('s'):
            cap.release()
            cv2.destroyAllWindows()
            return frame
        elif key == ord('q'):
            cap.release()
            cv2.destroyAllWindows()
            return None

# Fungsi untuk convert frame OpenCV ke format JPEG dan base64
def frame_to_base64(frame):
    _, buffer = cv2.imencode('.jpg', frame)
    jpg_as_text = base64.b64encode(buffer).decode('utf-8')
    return jpg_as_text

# Eksekusi
frame = capture_frame()

if frame is not None:
    print("Mengirim gambar ke Roboflow...")
    image_base64 = frame_to_base64(frame)

    response = requests.post(
        url="https://detect.roboflow.com/document-segmentation-v2-gt86h/2",
        params={
            "api_key": "tHovuYfATheJl3ayXOhU"
        },
        files={
            "image": image_base64
        }
    )

    if response.status_code == 200:
        print("✅ Hasil inference:")
        print(response.json())
    else:
        print("❌ Gagal infer:", response.status_code, response.text)
else:
    print("❌ Tidak ada frame yang di-capture.")
