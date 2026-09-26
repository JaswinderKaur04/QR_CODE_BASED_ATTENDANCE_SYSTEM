"""
Synchronize attendance records with Google Sheets.

The service account JSON file must be shared as an editor on the target Google Sheet.
"""
import json
import os
from pathlib import Path

from src.database import get_connection


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SHEET_NAME = "qr code based attendance data"
DEFAULT_WORKSHEET_NAME = "Attendance"
DEFAULT_CREDENTIAL_FILE = "qr-based-attendance-data-eecd3aa31350.json"
CREDENTIAL_ENV_VARS = (
    "GOOGLE_APPLICATION_CREDENTIALS",
    "GOOGLE_SHEETS_CREDENTIALS",
)


class GoogleSheetsSync:
    """Upload the complete attendance table to a Google Sheets worksheet."""

    HEADERS = [
        "Record ID",
        "Employee ID",
        "Employee Name",
        "Department",
        "Employee Email",
        "Employee Phone",
        "Date",
        "Check-In",
        "Check-Out",
        "Working Hours",
        "Punctuality",
        "Status",
    ]

    def __init__(
        self,
        sheet_name=None,
        worksheet_name=DEFAULT_WORKSHEET_NAME,
        credentials_path=None,
    ):
        self.sheet_name = sheet_name or os.getenv(
            "GOOGLE_SHEET_NAME", DEFAULT_SHEET_NAME
        )
        self.worksheet_name = worksheet_name
        self.credentials_path = self._find_credentials(credentials_path)
        self._client = None

    @staticmethod
    def _find_credentials(credentials_path=None):
        explicit_path = credentials_path or next(
            (os.getenv(name) for name in CREDENTIAL_ENV_VARS if os.getenv(name)),
            None,
        )
        if explicit_path:
            path = Path(explicit_path).expanduser()
            if not path.is_absolute():
                path = PROJECT_ROOT / path
            if not path.exists():
                raise FileNotFoundError(
                    f"Google service account file not found: {path}"
                )
            return path

        default_path = PROJECT_ROOT / DEFAULT_CREDENTIAL_FILE
        if default_path.exists():
            return default_path
        return None

    def _validate_credentials(self):
        if self.credentials_path is None:
            return

        try:
            credentials = json.loads(self.credentials_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(
                f"Unable to read Google service account file: {self.credentials_path}"
            ) from exc

        required_fields = {
            "type",
            "project_id",
            "client_email",
            "private_key_id",
            "private_key",
        }
        missing_fields = sorted(required_fields.difference(credentials))
        if missing_fields:
            raise ValueError(
                "Google service account file is missing: "
                + ", ".join(missing_fields)
            )
        if credentials.get("type") != "service_account":
            raise ValueError("Google credentials file must contain a service account")

    def _get_client(self):
        if self._client is not None:
            return self._client

        import gspread

        self._validate_credentials()
        self._client = gspread.service_account(
            filename=str(self.credentials_path),
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ],
        )
        return self._client

    def _get_worksheet(self, client):
        import gspread
        from gspread.exceptions import WorksheetNotFound

        matching_files = client.list_spreadsheet_files(title=self.sheet_name)
        if not matching_files:
            raise FileNotFoundError(
                f"Google Sheet not found: {self.sheet_name}"
            )
        if len(matching_files) > 1:
            file_ids = ", ".join(
                file_metadata["id"] for file_metadata in matching_files
            )
            raise ValueError(
                f"Multiple Google Sheets match '{self.sheet_name}': {file_ids}"
            )

        spreadsheet = client.open_by_key(matching_files[0]["id"])
        try:
            worksheet = spreadsheet.worksheet(self.worksheet_name)
        except WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(
                title=self.worksheet_name,
                rows=1000,
                cols=len(self.HEADERS),
                index=0,
            )

        worksheet.update_index(0)
        return worksheet

    @staticmethod
    def _get_records():
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                a.id,
                a.employee_id,
                a.date,
                a.time_in,
                a.time_out,
                a.working_hours,
                a.punctuality,
                a.status,
                e.name,
                e.department,
                e.email,
                e.phone
            FROM attendance a
            JOIN employees e ON e.employee_id = a.employee_id
            ORDER BY a.date, a.time_in, a.id
            """
        )
        records = cursor.fetchall()
        conn.close()
        return [dict(record) for record in records]

    @classmethod
    def _build_values(cls):
        records = cls._get_records()
        rows = [
            [
                record["id"],
                record["employee_id"],
                record["name"],
                record["department"],
                record["email"] or "",
                record["phone"] or "",
                record["date"],
                record["time_in"] or "",
                record["time_out"] or "",
                record["working_hours"],
                record["punctuality"],
                record["status"],
            ]
            for record in records
        ]
        return [cls.HEADERS] + rows

    def sync_all(self):
        """Replace the Attendance worksheet contents with all local records."""
        if self.credentials_path is None:
            return {
                "status": "skipped",
                "message": (
                    "Google Sheets sync is not configured. Set "
                    "GOOGLE_APPLICATION_CREDENTIALS or place the service account "
                    f"JSON file at {PROJECT_ROOT / DEFAULT_CREDENTIAL_FILE}."
                ),
                "records": 0,
            }

        client = self._get_client()
        worksheet = self._get_worksheet(client)
        values = self._build_values()
        worksheet.clear()
        worksheet.append_rows(values, value_input_option="RAW")
        worksheet.freeze(rows=1)

        return {
            "status": "success",
            "message": f"Synced {len(values) - 1} attendance records.",
            "records": len(values) - 1,
            "sheet": self.sheet_name,
            "worksheet": self.worksheet_name,
        }


def sync_attendance_to_google_sheets():
    """Convenience function used by the attendance manager and CLI."""
    return GoogleSheetsSync().sync_all()
