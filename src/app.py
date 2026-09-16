# How to Run This Project
# Step 1: Install Dependencies
# pip install -r requirements.txt
# Step 2: Populate Sample Data
# python main.py sample
# This adds 8 sample employees and generates their QR codes.

# Step 3: Start the Web Dashboard
# python main.py web
# The dashboard will be available at http://localhost:5000

# Other Commands
# python main.py scan - Start command-line webcam scanner
# python main.py qr - Generate QR codes for all employees


"""
Flask web application for the QR Code Attendance System.
Provides a web dashboard for scanning QR codes, viewing attendance, and analytics.
"""
import os
import sys
import base64
from io import BytesIO
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from PIL import Image

# Project root directory (parent of src/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Add project root to Python path for imports (works both via main.py and direct execution)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.attendance_manager import AttendanceManager
from src.qr_generator import generate_qr_code, generate_qr_codes_for_all_employees
from src.analytics import AttendanceAnalytics

app = Flask(
    __name__,
    template_folder=os.path.join(PROJECT_ROOT, "templates"),
    static_folder=os.path.join(PROJECT_ROOT, "static"),
)
app.secret_key = os.urandom(24)

# Initialize components
attendance_manager = AttendanceManager()
analytics = AttendanceAnalytics()


# ---------- Routes ----------

@app.route("/")
def index():
    """Render the home page with a summary of today's attendance."""
    stats = attendance_manager.get_statistics()
    today_records = attendance_manager.get_today_attendance()
    return render_template("index.html", stats=stats, today_records=today_records)


@app.route("/scan")
def scan_page():
    """Render the QR code scanning page."""
    return render_template("scan.html")


@app.route("/employees")
def employees_page():
    """Render the employee management page."""
    employees = attendance_manager.get_all_employees()
    return render_template("employees.html", employees=employees)


@app.route("/add_employee", methods=["GET", "POST"])
def add_employee():
    """Handle adding a new employee."""
    if request.method == "POST":
        employee_id = request.form.get("employee_id", "").strip()
        name = request.form.get("name", "").strip()
        department = request.form.get("department", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()

        if not employee_id or not name or not department:
            flash("Employee ID, Name, and Department are required.", "danger")
            return redirect(url_for("add_employee"))

        success = attendance_manager.add_employee(
            employee_id, name, department, email, phone
        )
        if success:
            # Generate QR code for the new employee
            generate_qr_code(employee_id, name=name)
            flash(f"Employee {employee_id} added successfully. QR code generated.", "success")
            return redirect(url_for("employees_page"))
        else:
            flash(f"Employee ID {employee_id} already exists.", "danger")
            return redirect(url_for("add_employee"))

    return render_template("add_employee.html")


@app.route("/generate_qr_codes")
def generate_qr_codes():
    """Generate QR codes for all employees."""
    results = generate_qr_codes_for_all_employees()
    flash(f"Generated {len(results)} QR codes.", "success")
    return redirect(url_for("employees_page"))


@app.route("/attendance")
def attendance_page():
    """Render the attendance records page."""
    date_filter = request.args.get("date", None)
    records = attendance_manager.get_attendance_records(date_str=date_filter)
    return render_template("attendance.html", records=records, date_filter=date_filter)


@app.route("/api/mark_attendance", methods=["POST"])
def api_mark_attendance():
    """
    API endpoint to mark attendance from a scanned QR code.

    Expects JSON: {"employee_id": "EMP001"}

    Returns:
        JSON: Result with status and message.
    """
    data = request.get_json()
    if not data or "employee_id" not in data:
        return jsonify({"status": "error", "message": "Missing employee_id"}), 400

    employee_id = data["employee_id"].strip()
    result = attendance_manager.mark_attendance(employee_id)
    return jsonify(result)


@app.route("/analytics")
def analytics_page():
    """Render the analytics dashboard with charts."""
    daily_chart = analytics.daily_attendance_chart()
    employee_chart = analytics.employee_wise_chart()
    department_chart = analytics.department_wise_chart()
    summary = analytics.attendance_summary_table()

    return render_template(
        "analytics.html",
        daily_chart=daily_chart.to_html(full_html=False, include_plotlyjs=False),
        employee_chart=employee_chart.to_html(full_html=False, include_plotlyjs=False),
        department_chart=department_chart.to_html(full_html=False, include_plotlyjs=False),
        summary=summary.to_html(classes="table table-striped", index=False),
    )


@app.route("/api/scan_qr", methods=["POST"])
def api_scan_qr():
    """
    API endpoint to scan a QR code from an uploaded image.

    Expects form data with an image file.

    Returns:
        JSON: Decoded QR code data.
    """
    if "qr_image" not in request.files:
        return jsonify({"status": "error", "message": "No image uploaded"}), 400

    image_file = request.files["qr_image"]
    if image_file.filename == "":
        return jsonify({"status": "error", "message": "No image selected"}), 400

    # Save and decode the image
    img = Image.open(image_file)
    img.save("temp_qr.png")

    from pyzbar.pyzbar import decode
    import cv2

    img_cv = cv2.imread("temp_qr.png")
    if img_cv is None:
        return jsonify({"status": "error", "message": "Failed to read image"}), 400

    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    qr_codes = decode(gray)

    if qr_codes:
        data = qr_codes[0].data.decode("utf-8")
        return jsonify({"status": "success", "employee_id": data})
    else:
        return jsonify({"status": "error", "message": "No QR code detected"}), 400


@app.route("/api/scan_frame", methods=["POST"])
def api_scan_frame():
    """
    API endpoint to scan a QR code from a camera frame (base64 image).

    Expects JSON: {"image": "base64-encoded-image-data"}

    Returns:
        JSON: Decoded QR code data or error.
    """
    import base64
    import io
    from pyzbar.pyzbar import decode
    import cv2
    import numpy as np

    data = request.get_json()
    if not data or "image" not in data:
        return jsonify({"status": "error", "message": "No image data"}), 400

    try:
        # Decode base64 image
        image_data = data["image"]
        if image_data.startswith("data:"):
            image_data = image_data.split(",", 1)[1]

        img_bytes = base64.b64decode(image_data)
        img_array = np.frombuffer(img_bytes, np.uint8)
        img_cv = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        if img_cv is None:
            return jsonify({"status": "error", "message": "Failed to decode image"}), 400

        # Detect QR code
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        qr_codes = decode(gray)

        if qr_codes:
            decoded_data = qr_codes[0].data.decode("utf-8")
            return jsonify({"status": "success", "employee_id": decoded_data})
        else:
            return jsonify({"status": "no_qr", "message": "No QR code detected"}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/qr_codes/<path:filename>")
def qr_code_image(filename):
    """Serve QR code images from the project's qr_codes directory."""
    from flask import send_from_directory
    qr_dir = os.path.join(PROJECT_ROOT, "qr_codes")
    return send_from_directory(qr_dir, filename)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)