"""
Authentication manager module.
Handles user login, registration, session management, and role-based access control.
"""
from datetime import datetime
from src.database import get_db, get_connection, hash_password


class AuthManager:
    """Manages user authentication and authorization."""

    def __init__(self):
        pass

    # ---------- User Management ----------

    def create_user(self, username, password, role="employee", employee_id=None):
        """
        Create a new user account.

        Args:
            username (str): Unique username.
            password (str): Plain text password (will be hashed).
            role (str): 'admin' or 'employee' (default 'employee').
            employee_id (str, optional): Link user to an employee record.

        Returns:
            bool: True if created, False if username already exists.
        """
        password_hash = hash_password(password)

        with get_db() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """INSERT INTO users (username, password_hash, role, employee_id)
                       VALUES (?, ?, ?, ?)""",
                    (username, password_hash, role, employee_id),
                )
                return True
            except Exception:
                return False

    def get_user_by_username(self, username):
        """Look up a user by username."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_user_by_id(self, user_id):
        """Look up a user by ID."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    # ---------- Authentication ----------

    def verify_login(self, username, password):
        """
        Verify a user's login credentials.

        Args:
            username (str): The username.
            password (str): The plain text password.

        Returns:
            dict or None: User record if credentials are valid, otherwise None.
        """
        user = self.get_user_by_username(username)
        if not user:
            return None

        password_hash = hash_password(password)
        if user["password_hash"] == password_hash:
            return user
        return None

    # ---------- Default Admin Setup ----------

    def create_default_admin(self, username="admin", password="admin123"):
        """
        Create a default admin account if no admin exists.

        Args:
            username (str): Admin username.
            password (str): Admin password.

        Returns:
            bool: True if created, False if admin already exists.
        """
        # Check if any admin exists
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1")
        existing = cursor.fetchone()
        conn.close()

        if existing:
            return False

        return self.create_user(username, password, role="admin")

    def create_employee_user(self, employee_id, username, password):
        """
        Create a user account linked to an employee.

        Args:
            employee_id (str): The employee ID to link.
            username (str): Username for the account.
            password (str): Plain text password.

        Returns:
            bool: True if created, False if username already exists.
        """
        return self.create_user(username, password, role="employee", employee_id=employee_id)


if __name__ == "__main__":
    auth = AuthManager()
    auth.create_default_admin()
    print("Default admin created: admin / admin123")