"""
Settings manager module.
Handles office timing configuration and punctuality rules.
"""
from datetime import datetime, time as dt_time
from src.database import get_db, get_connection


class SettingsManager:
    """Manages office settings like start time, end time, and late threshold."""

    DEFAULTS = {
        "office_start_time": "09:00",
        "office_end_time": "18:00",
        "late_threshold_minutes": "15",
        "auto_mark_absent": "true",
    }

    def __init__(self):
        pass

    def get_setting(self, key):
        """
        Get a setting value by key. Falls back to default if not found.

        Args:
            key (str): The setting key.

        Returns:
            str: The setting value.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        return row["value"] if row else self.DEFAULTS.get(key, "")

    def get_all_settings(self):
        """
        Get all settings as a dictionary.

        Returns:
            dict: All settings key-value pairs.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT key, value, description FROM settings ORDER BY key")
        rows = cursor.fetchall()
        conn.close()

        result = {}
        for row in rows:
            result[row["key"]] = {
                "value": row["value"],
                "description": row["description"]
            }

        # Merge with defaults for any missing keys
        for key, default_val in self.DEFAULTS.items():
            if key not in result:
                result[key] = {
                    "value": default_val,
                    "description": f"Default: {default_val}"
                }

        return result

    def update_setting(self, key, value):
        """
        Update a setting value.

        Args:
            key (str): The setting key.
            value (str): The new value.

        Returns:
            bool: True if updated, False on error.
        """
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT OR REPLACE INTO settings (key, value, updated_at)
                   VALUES (?, ?, CURRENT_TIMESTAMP)""",
                (key, str(value)),
            )
            return True

    def update_settings(self, settings_dict):
        """
        Update multiple settings at once.

        Args:
            settings_dict (dict): Dictionary of key-value pairs to update.

        Returns:
            bool: True if all updated successfully.
        """
        for key, value in settings_dict.items():
            self.update_setting(key, value)
        return True

    def get_office_start_time(self):
        """Get office start time as a datetime.time object."""
        time_str = self.get_setting("office_start_time")
        return self._parse_time(time_str)

    def get_office_end_time(self):
        """Get office end time as a datetime.time object."""
        time_str = self.get_setting("office_end_time")
        return self._parse_time(time_str)

    def get_late_threshold_minutes(self):
        """Get late threshold in minutes as an integer."""
        val = self.get_setting("late_threshold_minutes")
        try:
            return int(val)
        except (ValueError, TypeError):
            return 15

    def is_auto_mark_absent(self):
        """Check if auto-mark-absent is enabled."""
        val = self.get_setting("auto_mark_absent")
        return val.lower() in ("true", "1", "yes", "on")

    @staticmethod
    def _parse_time(time_str):
        """
        Parse a time string (HH:MM) into a datetime.time object.

        Args:
            time_str (str): Time string in HH:MM format.

        Returns:
            datetime.time: Parsed time object.
        """
        try:
            parts = time_str.strip().split(":")
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
            return dt_time(hour=hour, minute=minute)
        except (ValueError, IndexError):
            return dt_time(hour=9, minute=0)

    def classify_punctuality(self, time_in_str):
        """
        Classify an employee's punctuality based on check-in time.

        Args:
            time_in_str (str): Check-in time in HH:MM:SS format.

        Returns:
            str: 'Present', 'Late', or 'Early Departure' (for now just Present/Late).
        """
        if not time_in_str:
            return "Absent"

        try:
            parts = time_in_str.strip().split(":")
            check_in_hour = int(parts[0])
            check_in_minute = int(parts[1]) if len(parts) > 1 else 0
            check_in = dt_time(hour=check_in_hour, minute=check_in_minute)
        except (ValueError, IndexError):
            return "Present"

        office_start = self.get_office_start_time()
        late_threshold = self.get_late_threshold_minutes()

        # Calculate the deadline for being on time
        from datetime import timedelta
        deadline = (
            datetime.combine(datetime.today(), office_start)
            + timedelta(minutes=late_threshold)
        ).time()

        check_in_dt = datetime.combine(datetime.today(), check_in)

        if check_in_dt > datetime.combine(datetime.today(), deadline):
            return "Late"
        else:
            return "Present"


if __name__ == "__main__":
    sm = SettingsManager()
    print("Settings:", sm.get_all_settings())
    print("Office start:", sm.get_office_start_time())
    print("Classification for 09:10:", sm.classify_punctuality("09:10:00"))
    print("Classification for 09:30:", sm.classify_punctuality("09:30:00"))