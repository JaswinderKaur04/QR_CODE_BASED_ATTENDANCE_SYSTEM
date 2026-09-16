"""
Attendance manager module.
Handles marking attendance, preventing duplicates, and managing employee records.
"""
from datetime import datetime, date
from src.database import get_db, get_connection


class AttendanceManager:
    """Manages employee attendance records in the database."""

    def __init__(self):
        pass

    # ---------- Employee Management ----------

    def add_employee(self, employee_id, name, department, email=None, phone=None):
        """
        Add a new employee to the database.

        Args:
            employee_id (str): Unique employee ID.
            name (str): Employee name.
            department (str): Department name.
            email (str, optional): Employee email.
            phone (str, optional): Employee phone number.

        Returns:
            bool: True if added, False if employee_id already exists.
        """
        with get_db() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """INSERT INTO employees (employee_id, name, department, email, phone)
                       VALUES (?, ?, ?, ?, ?)""",
                    (employee_id, name, department, email, phone),
                )
                return True
            except sqlite3.IntegrityError:
                return False

    def get_all_employees(self):
        """Return all employees as a list of dictionaries."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM employees ORDER BY name")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_employee_by_id(self, employee_id):
        """
        Look up an employee by their employee_id.

        Args:
            employee_id (str): The employee ID to search for.

        Returns:
            dict or None: Employee record if found, otherwise None.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM employees WHERE employee_id = ?", (employee_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    # ---------- Attendance Management ----------

    def mark_attendance(self, employee_id):
        """
        Mark attendance for an employee for the current day.

        Args:
            employee_id (str): The employee ID from the scanned QR code.

        Returns:
            dict: Result with keys:
                - 'status': 'marked', 'already_marked', or 'not_found'
                - 'message': Human-readable message.
                - 'employee': Employee details (if found).
                - 'timestamp': Current timestamp (if marked).
        """
        # Check if employee exists
        employee = self.get_employee_by_id(employee_id)
        if not employee:
            return {
                "status": "not_found",
                "message": f"Employee Not Found: {employee_id}",
                "employee": None,
                "timestamp": None,
            }

        today = date.today().isoformat()
        now = datetime.now().strftime("%H:%M:%S")

        # Check if attendance already marked today
        if self._already_marked(employee_id, today):
            return {
                "status": "already_marked",
                "message": f"Already Marked: {employee['name']} ({employee_id})",
                "employee": employee,
                "timestamp": now,
            }

        # Mark attendance
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO attendance (employee_id, date, time_in, status)
                   VALUES (?, ?, ?, 'Present')""",
                (employee_id, today, now),
            )

        return {
            "status": "marked",
            "message": f"Attendance Marked: {employee['name']} ({employee_id})",
            "employee": employee,
            "timestamp": now,
        }

    def _already_marked(self, employee_id, date_str):
        """
        Check if attendance is already marked for an employee on a given date.

        Args:
            employee_id (str): Employee ID.
            date_str (str): Date in ISO format (YYYY-MM-DD).

        Returns:
            bool: True if already marked, False otherwise.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM attendance WHERE employee_id = ? AND date = ?",
            (employee_id, date_str),
        )
        row = cursor.fetchone()
        conn.close()
        return row is not None

    def get_attendance_records(self, employee_id=None, date_str=None):
        """
        Retrieve attendance records with optional filters.

        Args:
            employee_id (str, optional): Filter by employee ID.
            date_str (str, optional): Filter by date (YYYY-MM-DD).

        Returns:
            list: List of attendance record dictionaries.
        """
        conn = get_connection()
        cursor = conn.cursor()

        query = """
            SELECT a.id, a.employee_id, a.date, a.time_in, a.status,
                   e.name, e.department
            FROM attendance a
            JOIN employees e ON a.employee_id = e.employee_id
            WHERE 1 = 1
        """
        params = []

        if employee_id:
            query += " AND a.employee_id = ?"
            params.append(employee_id)

        if date_str:
            query += " AND a.date = ?"
            params.append(date_str)

        query += " ORDER BY a.date DESC, a.time_in DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_today_attendance(self):
        """Get all attendance records for today."""
        today = date.today().isoformat()
        return self.get_attendance_records(date_str=today)

    def get_statistics(self):
        """
        Compute attendance statistics.

        Returns:
            dict: Statistics including total employees, present today, etc.
        """
        from datetime import date as dt_date

        today = dt_date.today().isoformat()

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as total FROM employees")
        total_employees = cursor.fetchone()["total"]

        cursor.execute(
            "SELECT COUNT(*) as present FROM attendance WHERE date = ?", (today,)
        )
        present_today = cursor.fetchone()["present"]

        cursor.execute(
            "SELECT COUNT(DISTINCT employee_id) as total_marked FROM attendance WHERE date = ?",
            (today,),
        )
        unique_marked = cursor.fetchone()["total_marked"]

        conn.close()

        return {
            "total_employees": total_employees,
            "present_today": present_today,
            "unique_marked_today": unique_marked,
            "date": today,
        }


# Import sqlite3 for IntegrityError handling
import sqlite3

if __name__ == "__main__":
    manager = AttendanceManager()
    print("Attendance manager initialized.")
    stats = manager.get_statistics()
    print(f"Stats: {stats}")