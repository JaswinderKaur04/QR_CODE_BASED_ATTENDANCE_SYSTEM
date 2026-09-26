"""
Database module for the QR Code Attendance System.
Handles SQLite database connection and table creation.
"""
import sqlite3
from contextlib import contextmanager
import os
import hashlib

# Database file path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "attendance.db")


def get_connection():
    """Return a new SQLite connection with foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create the database tables if they do not exist."""
    conn = get_connection()
    cursor = conn.cursor()

    # Employees table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Attendance table - updated with check-in/check-out support
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            date TEXT NOT NULL,
            time_in TEXT,
            time_out TEXT,
            working_hours REAL,
            punctuality TEXT DEFAULT 'Present',
            status TEXT DEFAULT 'Present',
            FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
        )
    """)

    # Migration: add columns if they don't exist
    cursor.execute("PRAGMA table_info(attendance)")
    columns = [col[1] for col in cursor.fetchall()]
    if "time_out" not in columns:
        cursor.execute("ALTER TABLE attendance ADD COLUMN time_out TEXT")
    if "working_hours" not in columns:
        cursor.execute("ALTER TABLE attendance ADD COLUMN working_hours REAL")
    if "punctuality" not in columns:
        cursor.execute("ALTER TABLE attendance ADD COLUMN punctuality TEXT DEFAULT 'Present'")

    # Settings table for office timing configuration
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL,
            description TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Insert default settings
    cursor.execute("SELECT COUNT(*) as cnt FROM settings")
    if cursor.fetchone()["cnt"] == 0:
        cursor.execute(
            "INSERT INTO settings (key, value, description) VALUES (?, ?, ?)",
            ("office_start_time", "09:00", "Office start time (HH:MM format)")
        )
        cursor.execute(
            "INSERT INTO settings (key, value, description) VALUES (?, ?, ?)",
            ("office_end_time", "18:00", "Office end time (HH:MM format)")
        )
        cursor.execute(
            "INSERT INTO settings (key, value, description) VALUES (?, ?, ?)",
            ("late_threshold_minutes", "15", "Grace period in minutes before marking as Late")
        )
        cursor.execute(
            "INSERT INTO settings (key, value, description) VALUES (?, ?, ?)",
            ("auto_mark_absent", "true", "Automatically mark employees as Absent if not checked in by end of day")
        )

    # Index for faster duplicate checks
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_attendance
        ON attendance(employee_id, date)
    """)

    # Users table for authentication
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'employee',
            employee_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
        )
    """)

    conn.commit()
    conn.close()


def hash_password(password):
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")