"""
Main entry point for the QR Code Attendance System.

Usage:
    python main.py web        # Start the web dashboard
    python main.py scan      # Start webcam scanning
    python main.py sample    # Populate sample data
    python main.py qr        # Generate QR codes for all employees
    python main.py sync      # Upload all attendance records to Google Sheets
"""
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    command = sys.argv[1].lower()

    if command == "web":
        from src.app import app
        print("Starting web dashboard on http://0.0.0.0:5000")
        app.run(debug=True, host="0.0.0.0", port=5000)

    elif command == "scan":
        from src.qr_scanner import QRScanner
        from src.attendance_manager import AttendanceManager

        scanner = QRScanner()
        manager = AttendanceManager()

        def on_qr_scanned(employee_id):
            result = manager.mark_attendance(employee_id)
            print(f"\n>>> {result['message']}")

        print("Starting QR code scanner... Press 'q' to quit.")
        scanner.scan_continuous(callback=on_qr_scanned)

    elif command == "sample":
        from src.sample_data import populate_sample_data
        populate_sample_data()

    elif command == "qr":
        from src.qr_generator import generate_qr_codes_for_all_employees
        results = generate_qr_codes_for_all_employees()
        print(f"Generated {len(results)} QR codes.")
        for emp_id, path in results.items():
            print(f"  {emp_id} -> {path}")

    elif command == "sync":
        from src.google_sheets_sync import sync_attendance_to_google_sheets

        result = sync_attendance_to_google_sheets()
        print(result["message"])
        if result.get("status") == "error":
            return 1

    else:
        print(f"Unknown command: {command}")
        print(__doc__)


if __name__ == "__main__":
    main()