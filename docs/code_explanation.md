# Code Explanation

This document explains the important files and parts of the code in the QR Code Attendance System.

---

## 1. src/database.py

This module handles all SQLite database operations.

### Key Components:

**`get_connection()`**
- Returns a new SQLite connection with `row_factory = sqlite3.Row`, allowing access to columns by name.
- Enables foreign keys for referential integrity.

**`get_db()` (context manager)**
- Provides a connection that automatically commits on success or rolls back on error.
- Ensures the connection is always closed properly.

**`init_db()`**
- Creates two tables:
  - **employees**: Stores employee_id, name, department, email, phone, and creation timestamp.
  - **attendance**: Stores employee_id, date, time_in, and status.
- Creates a **unique index** on `(employee_id, date)` to prevent duplicate attendance for the same employee on the same day.

---

## 2. src/qr_generator.py

Generates unique QR codes for employees.

### Key Components:

**`generate_qr_code(employee_id, name, size, border)`**
- Uses the `qrcode` library to create a QR code with high error correction (`ERROR_CORRECT_H`).
- The QR code encodes only the `employee_id` string.
- Saves the image as a PNG file in the `qr_codes/` directory.
- Returns the file path.

**`generate_qr_codes_for_all_employees()`**
- Reads all employees from the database and generates a QR code for each.
- Returns a dictionary mapping employee_id to file path.

---

## 3. src/qr_scanner.py

Handles webcam-based QR code detection using OpenCV and pyzbar.

### Key Components:

**`QRScanner` class**
- **`start()`**: Opens the webcam using OpenCV's `VideoCapture`.
- **`read_frame()`**: Reads a single frame from the webcam.
- **`scan_qr_code(frame)`**: Converts the frame to grayscale and uses `pyzbar.decode()` to find and decode QR codes. Draws a green rectangle around detected codes.
- **`scan_once(timeout)`**: Scans until a QR code is found or the timeout expires. Includes a cooldown period to prevent rapid duplicate scans.
- **`scan_continuous(callback, window_name)`**: Continuously scans and displays the live feed in an OpenCV window. Calls the callback function when a QR code is detected. Exits when 'q' is pressed.

---

## 4. src/attendance_manager.py

Manages employee records and attendance marking.

### Key Components:

**`AttendanceManager` class**

**Employee Management:**
- **`add_employee(...)`**: Inserts a new employee. Returns `False` if the employee_id already exists (due to the UNIQUE constraint).
- **`get_all_employees()`**: Returns all employees as a list of dictionaries.
- **`get_employee_by_id(employee_id)`**: Looks up a single employee by their ID.

**Attendance Management:**
- **`mark_attendance(employee_id)`**: The core function that:
  1. Checks if the employee exists → returns "Employee Not Found" if not.
  2. Checks if attendance is already marked today → returns "Already Marked" if so.
  3. Inserts a new attendance record with the current date and time → returns "Attendance Marked".
- **`_already_marked(employee_id, date)`**: Internal helper that checks for existing attendance records.
- **`get_attendance_records(...)`**: Retrieves attendance records with optional filtering by employee_id and/or date.
- **`get_statistics()`**: Computes summary statistics (total employees, present today, etc.).

---

## 5. src/analytics.py

Provides attendance analytics using Pandas and Plotly.

### Key Components:

**`AttendanceAnalytics` class**

- **`get_attendance_dataframe(date_str)`**: Returns attendance records as a Pandas DataFrame.
- **`get_employee_dataframe()`**: Returns all employees as a Pandas DataFrame.
- **`daily_attendance_chart()`**: Generates a bar chart showing employees who marked attendance today, sorted by time-in.
- **`employee_wise_chart()`**: Generates a bar chart showing total days present per employee.
- **`department_wise_chart()`**: Generates a pie chart showing the distribution of attendance across departments.
- **`attendance_summary_table()`**: Returns a summary DataFrame with each employee's total days present and last attendance date.
- **`get_html_fig(fig)`**: Converts a Plotly figure to an HTML string for embedding in web templates.

---

## 6. src/app.py

The Flask web application that provides the dashboard UI.

### Key Components:

**Routes:**
- **`/` (index)**: Home page showing today's attendance summary.
- **`/scan`**: QR code scanning page with webcam and image upload options.
- **`/employees`**: Employee management page listing all employees with their QR codes.
- **`/add_employee`**: Form to add a new employee (POST handler adds to database and generates QR code).
- **`/generate_qr_codes`**: Generates QR codes for all employees.
- **`/attendance`**: Attendance records page with date filtering.
- **`/analytics`**: Analytics dashboard with three charts and a summary table.
- **`/api/mark_attendance`**: API endpoint that receives a scanned employee_id and marks attendance. Returns JSON with status and message.
- **`/api/scan_qr`**: API endpoint that receives an uploaded QR code image, decodes it, and returns the employee_id.

**Technology notes:**
- Uses Flask for the web server.
- The scan page uses the `html5-qrcode` JavaScript library for webcam scanning in the browser, which is more reliable than OpenCV's Python GUI.
- The image upload API uses pyzbar for decoding.

---

## 7. templates/

HTML templates using Bootstrap 5 for responsive design.

- **`layout.html`**: Base template with navigation bar and flash message handling.
- **`index.html`**: Home page with summary cards and today's attendance table.
- **`scan.html`**: QR scanning page with camera controls, image upload, and result display.
- **`employees.html`**: Employee table with QR code images.
- **`add_employee.html`**: Form for adding new employees.
- **`attendance.html`**: Attendance records with date filter.
- **`analytics.html`**: Dashboard with three Plotly charts and a summary table.

---

## 8. main.py

The command-line entry point. Supports four commands:

- `python main.py web` — Starts the Flask web dashboard.
- `python main.py scan` — Starts the command-line webcam scanner.
- `python main.py sample` — Populates the database with sample employees and generates QR codes.
- `python main.py qr` — Generates QR codes for all employees.

---

## How the System Prevents Duplicate Attendance

The database has a unique index on `(employee_id, date)` in the `attendance` table. Additionally, the `mark_attendance()` method explicitly checks for existing records before inserting. This double-layered approach ensures that an employee can only be marked present once per day, even if the same QR code is scanned multiple times.

## Message System

The `mark_attendance()` method returns a dictionary with:
- `status`: One of `"marked"`, `"already_marked"`, or `"not_found"`.
- `message`: A human-readable message like "Attendance Marked: Alice Johnson (EMP001)".
- `employee`: Employee details if found.
- `timestamp`: The current time if applicable.

These messages are displayed to the user via flash messages in the web UI or printed to the console in CLI mode.