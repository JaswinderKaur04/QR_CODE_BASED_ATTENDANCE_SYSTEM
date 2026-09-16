"""
Sample data script.
Populates the database with sample employees and generates their QR codes.
"""
from src.database import init_db
from src.attendance_manager import AttendanceManager
from src.qr_generator import generate_qr_codes_for_all_employees


SAMPLE_EMPLOYEES = [
    {"employee_id": "EMP001", "name": "Alice Johnson", "department": "Engineering", "email": "alice@company.com", "phone": "+1234567890"},
    {"employee_id": "EMP002", "name": "Bob Smith", "department": "Engineering", "email": "bob@company.com", "phone": "+1234567891"},
    {"employee_id": "EMP003", "name": "Carol White", "department": "Marketing", "email": "carol@company.com", "phone": "+1234567892"},
    {"employee_id": "EMP004", "name": "David Brown", "department": "Sales", "email": "david@company.com", "phone": "+1234567893"},
    {"employee_id": "EMP005", "name": "Eve Davis", "department": "HR", "email": "eve@company.com", "phone": "+1234567894"},
    {"employee_id": "EMP006", "name": "Frank Miller", "department": "Finance", "email": "frank@company.com", "phone": "+1234567895"},
    {"employee_id": "EMP007", "name": "Grace Wilson", "department": "Engineering", "email": "grace@company.com", "phone": "+1234567896"},
    {"employee_id": "EMP008", "name": "Henry Moore", "department": "Marketing", "email": "henry@company.com", "phone": "+1234567897"},
]


def populate_sample_data():
    """Add sample employees to the database and generate QR codes."""
    init_db()
    manager = AttendanceManager()

    for emp in SAMPLE_EMPLOYEES:
        success = manager.add_employee(
            emp["employee_id"],
            emp["name"],
            emp["department"],
            emp.get("email"),
            emp.get("phone"),
        )
        if success:
            print(f"Added: {emp['employee_id']} - {emp['name']}")
        else:
            print(f"Skipped (already exists): {emp['employee_id']}")

    # Generate QR codes
    print("\nGenerating QR codes...")
    results = generate_qr_codes_for_all_employees()
    for emp_id, path in results.items():
        print(f"  {emp_id} -> {path}")

    print(f"\nDone! Added {len(SAMPLE_EMPLOYEES)} sample employees.")


if __name__ == "__main__":
    populate_sample_data()