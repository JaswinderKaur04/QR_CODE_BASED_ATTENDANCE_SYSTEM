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
from functools import wraps
from io import BytesIO
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from PIL import Image

# Project root directory (parent of src/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Add project root to Python path for imports (works both via main.py and direct execution)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.attendance_manager import AttendanceManager
from src.qr_generator import generate_qr_code, generate_qr_codes_for_all_employees
from src.analytics import AttendanceAnalytics
from src.auth_manager import AuthManager
from src.settings_manager import SettingsManager
from src.database import init_db, hash_password

app = Flask(
    __name__,
    template_folder=os.path.join(PROJECT_ROOT, "templates"),
    static_folder=os.path.join(PROJECT_ROOT, "static"),
)
app.secret_key = os.urandom(24)

# Initialize components
attendance_manager = AttendanceManager()
analytics = AttendanceAnalytics()
auth_manager = AuthManager()
settings_manager = SettingsManager()

# Initialize database and create default admin
init_db()
auth_manager.create_default_admin()


# ---------- Authentication Helpers ----------

def login_required(f):
    """Decorator to require login for accessing a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require admin role for accessing a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login_page"))
        if session.get("user_role") != "admin":
            flash("Access denied. Admin privileges required.", "danger")
            return redirect(url_for("scan_page"))
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    """Get the currently logged-in user from session."""
    if "user_id" in session:
        return auth_manager.get_user_by_id(session["user_id"])
    return None


# ---------- Authentication Routes ----------

@app.route("/login", methods=["GET", "POST"])
def login_page():
    """Handle user login."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Username and password are required.", "danger")
            return render_template("login.html")

        user = auth_manager.verify_login(username, password)
        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["user_role"] = user["role"]
            session["employee_id"] = user["employee_id"]

            flash("Welcome back, " + user["username"] + "!", "success")
            # Redirect based on role
            if user["role"] == "admin":
                return redirect(url_for("index"))
            else:
                return redirect(url_for("scan_page"))
        else:
            flash("Invalid username or password.", "danger")
            return render_template("login.html")

    return render_template("login.html")


@app.route("/logout")
def logout_page():
    """Log out the current user."""
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login_page"))


@app.route("/register", methods=["GET", "POST"])
def register_page():
    """Handle user registration."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()
        employee_id = request.form.get("employee_id", "").strip()

        if not username or not password:
            flash("Username and password are required.", "danger")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")

        if len(password) < 4:
            flash("Password must be at least 4 characters.", "danger")
            return render_template("register.html")

        success = auth_manager.create_employee_user(employee_id, username, password)
        if success:
            flash("Account created successfully. Please log in.", "success")
            return redirect(url_for("login_page"))
        else:
            flash("Username already exists.", "danger")
            return render_template("register.html")

    return render_template("register.html")


# ---------- Protected Routes ----------

@app.route("/")
@admin_required
def index():
    """Render the home page with a summary of today's attendance."""
    stats = attendance_manager.get_statistics()
    today_records = attendance_manager.get_today_attendance()
    current_user = get_current_user()
    return render_template("index.html", stats=stats, today_records=today_records, user=current_user)


@app.route("/scan")
@login_required
def scan_page():
    """Render the QR code scanning page."""
    current_user = get_current_user()
    return render_template("scan.html", user=current_user)


@app.route("/employees")
@admin_required
def employees_page():
    """Render the employee management page."""
    employees = attendance_manager.get_all_employees()
    return render_template("employees.html", employees=employees)


@app.route("/add_employee", methods=["GET", "POST"])
@admin_required
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
@admin_required
def generate_qr_codes():
    """Generate QR codes for all employees."""
    results = generate_qr_codes_for_all_employees()
    flash(f"Generated {len(results)} QR codes.", "success")
    return redirect(url_for("employees_page"))


@app.route("/attendance")
@admin_required
def attendance_page():
    """Render the attendance records page."""
    date_filter = request.args.get("date", None)
    records = attendance_manager.get_attendance_records(date_str=date_filter)
    current_user = get_current_user()
    return render_template("attendance.html", records=records, date_filter=date_filter, user=current_user)


@app.route("/api/mark_attendance", methods=["POST"])
def api_mark_attendance():
    """
    API endpoint to mark attendance from a scanned QR code.
    Supports both check-in and check-out.

    Expects JSON: {"employee_id": "EMP001", "action": "check_in|check_out"}

    Returns:
        JSON: Result with status and message.
    """
    data = request.get_json()
    if not data or "employee_id" not in data:
        return jsonify({"status": "error", "message": "Missing employee_id"}), 400

    employee_id = data["employee_id"].strip()
    action = data.get("action", "check_in").strip().lower()
    if action not in ("check_in", "check_out"):
        action = "check_in"

    result = attendance_manager.mark_attendance(employee_id, action=action)
    return jsonify(result)


@app.route("/analytics")
@admin_required
def analytics_page():
    """Render the analytics dashboard with charts."""
    daily_chart = analytics.daily_attendance_chart()
    employee_chart = analytics.employee_wise_chart()
    department_chart = analytics.department_wise_chart()
    working_hours_chart = analytics.working_hours_chart()
    punctuality_chart = analytics.punctuality_chart()
    summary = analytics.attendance_summary_table()

    return render_template(
        "analytics.html",
        daily_chart=daily_chart.to_html(full_html=False, include_plotlyjs=False),
        employee_chart=employee_chart.to_html(full_html=False, include_plotlyjs=False),
        department_chart=department_chart.to_html(full_html=False, include_plotlyjs=False),
        working_hours_chart=working_hours_chart.to_html(full_html=False, include_plotlyjs=False),
        punctuality_chart=punctuality_chart.to_html(full_html=False, include_plotlyjs=False),
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


@app.route("/settings", methods=["GET", "POST"])
@admin_required
def settings_page():
    """Handle office settings configuration."""
    if request.method == "POST":
        start_time = request.form.get("office_start_time", "09:00").strip()
        end_time = request.form.get("office_end_time", "18:00").strip()
        late_threshold = request.form.get("late_threshold_minutes", "15").strip()
        auto_absent = request.form.get("auto_mark_absent", "off")

        settings_manager.update_settings({
            "office_start_time": start_time,
            "office_end_time": end_time,
            "late_threshold_minutes": late_threshold,
            "auto_mark_absent": "true" if auto_absent == "on" else "false",
        })
        flash("Settings updated successfully.", "success")
        return redirect(url_for("settings_page"))

    settings = settings_manager.get_all_settings()
    current_user = get_current_user()
    return render_template("settings.html", settings=settings, user=current_user)


@app.route("/api/mark_absent", methods=["POST"])
def api_mark_absent():
    """API endpoint to manually mark absent employees for today."""
    if not session.get("user_id"):
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    if session.get("user_role") != "admin":
        return jsonify({"status": "error", "message": "Admin privileges required"}), 403

    count = attendance_manager.mark_absent_employees()
    return jsonify({"status": "success", "message": f"Marked {count} employees as absent.", "count": count})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)