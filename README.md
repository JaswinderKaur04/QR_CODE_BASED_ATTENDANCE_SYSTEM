# QR Code Based Employee Attendance System

A complete, modular attendance system built with Python. Employees scan a unique QR code (generated from their Employee ID) using a webcam or by uploading an image. The system marks their attendance with date and time, prevents duplicate entries for the same day, and provides an analytics dashboard with Pandas and Plotly.

## Features

- **QR Code Generation**: Unique QR codes generated for each employee using their Employee ID.
- **Webcam Scanning**: Real-time QR code detection using OpenCV and pyzbar.
- **Image Upload**: Upload QR code images for scanning.
- **Duplicate Prevention**: Each employee can only be marked present once per day.
- **Clear Feedback**: Shows "Attendance Marked", "Already Marked", or "Employee Not Found".
- **SQLite Storage**: All employee details and attendance records stored in SQLite.
- **Analytics Dashboard**: Daily, employee-wise, and department-wise attendance charts using Plotly.
- **Web Interface**: Flask-based dashboard with a clean UI.

## Project Structure

```
qr_code_based_attendance_system/
├── main.py              # Entry point
├── requirements.txt     # Python dependencies
├── src/
│   ├── database.py       # SQLite database connection and schema
│   ├── qr_generator.py  # QR code generation
│   ├── qr_scanner.py    # Webcam-based QR scanning
│   ├── attendance_manager.py  # Attendance logic and employee management
│   ├── analytics.py     # Pandas + Plotly analytics
│   ├── app.py           # Flask web application
│   └── sample_data.py   # Sample employee data
├── templates/           # HTML templates
│   ├── layout.html      # Base layout
│   ├── index.html       # Home page
│   ├── scan.html        # QR scanning page
│   ├── employees.html   # Employee management
│   ├── add_employee.html # Add employee form
│   ├── attendance.html  # Attendance records
│   └── analytics.html   # Analytics dashboard
├── static/
│   └── css/
│       └── style.css    # Custom CSS
├── qr_codes/            # Generated QR code images
└── docs/                # Documentation
```

## Installation

1. Install the required packages:
```bash
pip install -r requirements.txt
```

2. Populate the database with sample data:
```bash
python main.py sample
```

3. Start the web dashboard:
```bash
python main.py web
```

4. Open your browser and go to `http://localhost:5000`

## Usage

### Web Dashboard
- **Home**: View today's attendance summary
- **Scan QR**: Use webcam or upload image to scan QR codes
- **Employees**: View and manage employees, generate QR codes
- **Attendance**: View attendance records with date filtering
- **Analytics**: View interactive charts and summary tables

### Command Line Scanner
```bash
python main.py scan
```
This opens the webcam and continuously scans QR codes, printing results to the console.

### Generate QR Codes
```bash
python main.py qr
```
Generates QR codes for all employees in the database.

## How It Works

1. Each employee has a unique QR code generated from their Employee ID.
2. When scanned, the system decodes the QR code to get the Employee ID.
3. The system checks if the employee exists in the database.
4. If not found, returns "Employee Not Found".
5. If found, checks if attendance is already marked for today.
6. If already marked, returns "Already Marked".
7. If not marked, inserts a new attendance record with current date and time.
8. Returns "Attendance Marked".

## Technologies Used
- **QR Code Generation**: qrcode, Pillow
- **QR Code Detection**: OpenCV, pyzbar, html5-qrcode
- **Web Framework**: Flask
- **Database**: SQLite
- **Data Handling**: Pandas
- **Visualization**: Plotly
- **Frontend**: Bootstrap 5, HTML/CSS/JavaScript

## License
This project uses only free/open-source libraries. No paid APIs, images, or services are used.