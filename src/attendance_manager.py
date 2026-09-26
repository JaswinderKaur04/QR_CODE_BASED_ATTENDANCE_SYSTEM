"""
Attendance manager module.
Handles marking attendance, preventing duplicates, and managing employee records.
"""
from datetime import datetime, date
from src.database import get_db, get_connection
from src.settings_manager import SettingsManager


class AttendanceManager:
    """Manages employee attendance records in the database."""

    def __init__(self):
        self.settings = SettingsManager()
        self._google_sheets_sync = None

    def _sync_google_sheet(self):
        try:
            from src.google_sheets_sync import GoogleSheetsSync

            if self._google_sheets_sync is None:
                self._google_sheets_sync = GoogleSheetsSync()
            return self._google_sheets_sync.sync_all()
        except Exception as exc:
            return {
                "status": "error",
                "message": f"Google Sheets sync failed: {exc}",
            }

    def sync_google_sheet(self):
        """Synchronize all attendance records with Google Sheets."""
        return self._sync_google_sheet()

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

    def mark_attendance(self, employee_id, action="check_in"):
        """
        Mark attendance for an employee for the current day.
        Supports both check-in and check-out actions.

        Args:
            employee_id (str): The employee ID from the scanned QR code.
            action (str): 'check_in' or 'check_out' (default: 'check_in').

        Returns:
            dict: Result with keys:
                - 'status': 'marked', 'already_marked', 'not_found', 'checked_out', or 'error'
                - 'message': Human-readable message.
                - 'employee': Employee details (if found).
                - 'timestamp': Current timestamp.
                - 'working_hours': Total working hours (if check-out).
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

        # Check existing attendance record for today
        existing = self._get_attendance_record(employee_id, today)

        if action == "check_in":
            if existing:
                # Already checked in today
                if existing["time_out"]:
                    return {
                        "status": "already_marked",
                        "message": f"Already Checked In & Out: {employee['name']} ({employee_id})",
                        "employee": employee,
                        "timestamp": now,
                    }
                return {
                    "status": "already_marked",
                    "message": f"Already Checked In: {employee['name']} ({employee_id}) at {existing['time_in']}",
                    "employee": employee,
                    "timestamp": now,
                }

            # Insert new check-in record with punctuality classification
            punctuality = self.settings.classify_punctuality(now)
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO attendance (employee_id, date, time_in, punctuality, status)
                       VALUES (?, ?, ?, ?, 'Present')""",
                    (employee_id, today, now, punctuality),
                )

            sync_result = self._sync_google_sheet()
            return {
                "status": "marked",
                "message": f"Check-In Marked: {employee['name']} ({employee_id}) at {now}",
                "employee": employee,
                "timestamp": now,
                "punctuality": punctuality,
                "google_sheet_sync": sync_result,
            }

        elif action == "check_out":
            if not existing:
                return {
                    "status": "error",
                    "message": f"Cannot check out: {employee['name']} ({employee_id}) has not checked in today.",
                    "employee": employee,
                    "timestamp": now,
                }

            if existing["time_out"]:
                return {
                    "status": "already_marked",
                    "message": f"Already Checked Out: {employee['name']} ({employee_id}) at {existing['time_out']}",
                    "employee": employee,
                    "timestamp": now,
                }

            # Calculate working hours
            time_in_str = existing["time_in"]
            time_in_dt = datetime.strptime(time_in_str, "%H:%M:%S")
            time_out_dt = datetime.strptime(now, "%H:%M:%S")
            working_hours = (time_out_dt - time_in_dt).total_seconds() / 3600.0

            # Update record with check-out time and working hours
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """UPDATE attendance
                       SET time_out = ?, working_hours = ?
                       WHERE employee_id = ? AND date = ?""",
                    (now, round(working_hours, 2), employee_id, today),
                )

            sync_result = self._sync_google_sheet()
            return {
                "status": "checked_out",
                "message": f"Check-Out Marked: {employee['name']} ({employee_id}) at {now}. Total: {working_hours:.2f} hrs",
                "employee": employee,
                "timestamp": now,
                "working_hours": round(working_hours, 2),
                "google_sheet_sync": sync_result,
            }

        else:
            return {
                "status": "error",
                "message": f"Invalid action: {action}. Use 'check_in' or 'check_out'.",
                "employee": employee,
                "timestamp": now,
            }

    def _get_attendance_record(self, employee_id, date_str):
        """
        Get the attendance record for an employee on a given date.

        Args:
            employee_id (str): Employee ID.
            date_str (str): Date in ISO format (YYYY-MM-DD).

        Returns:
            dict or None: Attendance record if found, otherwise None.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, employee_id, date, time_in, time_out, working_hours, punctuality, status "
            "FROM attendance WHERE employee_id = ? AND date = ?",
            (employee_id, date_str),
        )
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

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
            SELECT a.id, a.employee_id, a.date, a.time_in, a.time_out,
                   a.working_hours, a.punctuality, a.status,
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

    def mark_absent_employees(self, date_str=None):
        """
        Mark all employees who haven't checked in as Absent for the given date.

        Args:
            date_str (str, optional): Date to process (default: today).

        Returns:
            int: Number of employees marked absent.
        """
        if not self.settings.is_auto_mark_absent():
            return 0

        if date_str is None:
            date_str = date.today().isoformat()

        conn = get_connection()
        cursor = conn.cursor()

        # Get all employees who don't have an attendance record for this date
        cursor.execute(
            """SELECT e.employee_id FROM employees e
               WHERE e.employee_id NOT IN (
                   SELECT a.employee_id FROM attendance a WHERE a.date = ?
               )""",
            (date_str,),
        )
        absent_employees = cursor.fetchall()

        count = 0
        for emp in absent_employees:
            try:
                cursor.execute(
                    """INSERT INTO attendance (employee_id, date, time_in, punctuality, status)
                       VALUES (?, ?, NULL, 'Absent', 'Absent')""",
                    (emp["employee_id"], date_str),
                )
                count += 1
            except Exception:
                pass

        conn.commit()
        conn.close()

        if count:
            self._sync_google_sheet()
        return count

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

        cursor.execute(
            "SELECT COUNT(*) as checked_out FROM attendance WHERE date = ? AND time_out IS NOT NULL",
            (today,),
        )
        checked_out_today = cursor.fetchone()["checked_out"]

        cursor.execute(
            "SELECT COUNT(*) as late FROM attendance WHERE date = ? AND punctuality = 'Late'",
            (today,),
        )
        late_today = cursor.fetchone()["late"]

        cursor.execute(
            "SELECT COUNT(*) as absent FROM attendance WHERE date = ? AND punctuality = 'Absent'",
            (today,),
        )
        absent_today = cursor.fetchone()["absent"]

        cursor.execute(
            "SELECT AVG(working_hours) as avg_hours FROM attendance WHERE date = ? AND working_hours IS NOT NULL",
            (today,),
        )
        avg_hours_row = cursor.fetchone()
        avg_working_hours = round(avg_hours_row["avg_hours"], 2) if avg_hours_row["avg_hours"] else 0

        conn.close()

        return {
            "total_employees": total_employees,
            "present_today": present_today,
            "unique_marked_today": unique_marked,
            "checked_out_today": checked_out_today,
            "late_today": late_today,
            "absent_today": absent_today,
            "avg_working_hours_today": avg_working_hours,
            "date": today,
        }


# Import sqlite3 for IntegrityError handling
import sqlite3

if __name__ == "__main__":
    manager = AttendanceManager()
    print("Attendance manager initialized.")
    stats = manager.get_statistics()
    print(f"Stats: {stats}")