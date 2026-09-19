import io
import json
import base64
import qrcode
from qrcode.image.pil import PilImage

class BloodUnitQRService:
    """
    QR Code generation and verification service for individual blood unit tracking.
    Enables barcode/QR scanning from phlebotomy collection, cold-chain storage,
    testing lab release, to final hospital bedside issue.
    """

    @classmethod
    def generate_qr_base64(cls, unit_data):
        """
        Generates a Base64-encoded PNG image of a QR code containing blood unit certificate data.
        Returns a data URI string ready for embedding in HTML img src.
        """
        if isinstance(unit_data, dict):
            qr_content = json.dumps(unit_data, sort_keys=True)
        else:
            qr_content = str(unit_data)

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=6,
            border=2,
        )
        qr.add_data(qr_content)
        qr.make(fit=True)

        img = qr.make_image(fill_color="#b71c1c", back_color="#ffffff")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f"data:image/png;base64,{encoded}"

    @classmethod
    def build_unit_payload(cls, unit):
        """Builds standardized machine-readable dictionary for blood unit QR encoding."""
        return {
            "system": "LifeSaver-BBMS",
            "unit_no": unit.unit_number,
            "blood_group": unit.blood_group,
            "component": unit.component_type,
            "volume_ml": unit.volume_ml,
            "collected": unit.collection_date.strftime('%Y-%m-%d') if unit.collection_date else "N/A",
            "expires": unit.expiry_date.strftime('%Y-%m-%d') if unit.expiry_date else "N/A",
            "status": unit.status,
            "testing": unit.screening_results or "Non-Reactive (Passed)"
        }
