from flask import Blueprint, request, jsonify, Response
from ..services.scan_service import ScanService, ScanError

# Buat instance Blueprint
scanner_bp = Blueprint('scanner_bp', __name__)

# Service akan di-inject dari file utama aplikasi
scan_service: ScanService = None


def init_scanner_api(service_instance: ScanService):
    """Menerima instance service yang sudah dibuat."""
    global scan_service
    scan_service = service_instance


@scanner_bp.route('/scan', methods=['POST'])
def scan_endpoint():
    """Endpoint untuk menerima file gambar dan mengembalikan hasil pindaian."""
    if scan_service is None:
        return jsonify({"error": "Layanan pemindaian belum diinisialisasi."}), 503

    if 'file' not in request.files:
        return jsonify({"error": "Request harus menyertakan 'file'."}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Tidak ada file yang dipilih."}), 400

    try:
        # Baca file sebagai bytes
        image_bytes = file.read()

        # Panggil service untuk memproses gambar
        cleaned_image_bytes = scan_service.process_image(image_bytes)

        # Kembalikan hasilnya sebagai gambar
        return Response(cleaned_image_bytes, mimetype='image/jpeg')

    except ScanError as e:
        # Jika terjadi error yang terkendali dari service
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        # Untuk error tak terduga lainnya
        return jsonify({"error": f"Terjadi kesalahan internal: {e}"}), 500
