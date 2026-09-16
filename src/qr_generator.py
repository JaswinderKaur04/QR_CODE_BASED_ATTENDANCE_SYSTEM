"""
QR Code generator module.
Generates unique QR codes for employees based on their Employee ID.
"""
import os
import qrcode
from PIL import Image

# Output directory for generated QR codes
QR_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "qr_codes")


def generate_qr_code(employee_id, name=None, size=10, border=4):
    """
    Generate a QR code for the given employee ID and save it to the qr_codes folder.

    Args:
        employee_id (str): The employee ID to encode.
        name (str, optional): Optional name to add as a label on the QR code.
        size (int): QR code size in blocks (default 10).
        border (int): Border size in blocks (default 4).

    Returns:
        str: Path to the saved QR code image.
    """
    os.makedirs(QR_DIR, exist_ok=True)

    # Create QR code instance
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=size,
        border=border,
    )
    qr.add_data(employee_id)
    qr.make(fit=True)

    # Generate the QR code image
    img = qr.make_image(fill_color="black", back_color="white")
    img = img.convert("RGB")

    # Save the image
    safe_name = employee_id.replace("/", "_").replace("\\", "_")
    filename = f"{safe_name}.png"
    filepath = os.path.join(QR_DIR, filename)
    img.save(filepath)

    return filepath


def generate_qr_codes_for_all_employees(db_path=None):
    """
    Generate QR codes for all employees in the database.

    Args:
        db_path (str, optional): Path to the database file.

    Returns:
        dict: Mapping of employee_id to QR code file path.
    """
    from src.database import get_connection

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT employee_id, name FROM employees")
    rows = cursor.fetchall()
    conn.close()

    results = {}
    for row in rows:
        emp_id = row["employee_id"]
        name = row["name"]
        path = generate_qr_code(emp_id, name=name)
        results[emp_id] = path

    return results


if __name__ == "__main__":
    # Test generation
    path = generate_qr_code("EMP001", name="John Doe")
    print(f"QR code generated at: {path}")