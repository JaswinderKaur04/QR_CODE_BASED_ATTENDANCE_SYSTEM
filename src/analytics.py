"""
Analytics module.
Uses Pandas for data handling and Plotly for attendance analytics visualizations.
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, date as dt_date
from src.attendance_manager import AttendanceManager


class AttendanceAnalytics:
    """Provides attendance analytics and visualization using Pandas and Plotly."""

    def __init__(self):
        self.manager = AttendanceManager()

    def get_attendance_dataframe(self, date_str=None):
        """
        Get attendance records as a Pandas DataFrame.

        Args:
            date_str (str, optional): Filter by date (YYYY-MM-DD).

        Returns:
            pd.DataFrame: DataFrame containing attendance records.
        """
        records = self.manager.get_attendance_records(date_str=date_str)
        if not records:
            return pd.DataFrame(
                columns=["id", "employee_id", "date", "time_in", "time_out", "working_hours", "punctuality", "status", "name", "department"]
            )
        df = pd.DataFrame(records)
        return df

    def get_employee_dataframe(self):
        """Get all employees as a Pandas DataFrame."""
        employees = self.manager.get_all_employees()
        if not employees:
            return pd.DataFrame(
                columns=["id", "employee_id", "name", "department", "email", "phone"]
            )
        return pd.DataFrame(employees)

    def daily_attendance_chart(self, date_str=None):
        """
        Generate a bar chart showing daily attendance.

        Args:
            date_str (str, optional): Date to filter by (default: today).

        Returns:
            plotly.graph_objects.Figure: A bar chart figure.
        """
        if date_str is None:
            date_str = dt_date.today().isoformat()

        df = self.get_attendance_dataframe(date_str=date_str)

        if df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No attendance records for this date",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor="center", yanchor="middle",
                showarrow=False
            )
            fig.update_layout(title="Daily Attendance")
            return fig

        # Sort by time_in
        df = df.sort_values("time_in")

        fig = px.bar(
            df,
            x="name",
            y="time_in",
            color="department",
            title=f"Daily Attendance - {date_str}",
            labels={"name": "Employee Name", "time_in": "Time In", "department": "Department"},
            hover_data=["employee_id", "status"],
        )
        fig.update_layout(
            xaxis_tickangle=-45,
            bargap=0.2,
        )
        return fig

    def employee_wise_chart(self):
        """
        Generate a bar chart showing total attendance per employee over time.

        Returns:
            plotly.graph_objects.Figure: A bar chart figure.
        """
        df = self.get_attendance_dataframe()

        if df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No attendance records available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor="center", yanchor="middle",
                showarrow=False
            )
            fig.update_layout(title="Employee-wise Attendance")
            return fig

        # Count attendance per employee
        counts = df.groupby(["employee_id", "name", "department"]).size().reset_index(name="total_present")
        counts = counts.sort_values("total_present", ascending=False)

        fig = px.bar(
            counts,
            x="name",
            y="total_present",
            color="department",
            title="Employee-wise Total Attendance",
            labels={"name": "Employee Name", "total_present": "Days Present", "department": "Department"},
            hover_data=["employee_id"],
        )
        fig.update_layout(xaxis_tickangle=-45, bargap=0.2)
        return fig

    def department_wise_chart(self):
        """
        Generate a pie chart showing department-wise attendance distribution.

        Returns:
            plotly.graph_objects.Figure: A pie chart figure.
        """
        df = self.get_attendance_dataframe()

        if df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No attendance records available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor="center", yanchor="middle",
                showarrow=False
            )
            fig.update_layout(title="Department-wise Attendance")
            return fig

        # Count by department
        dept_counts = df.groupby("department").size().reset_index(name="count")

        fig = px.pie(
            dept_counts,
            values="count",
            names="department",
            title="Department-wise Attendance Distribution",
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        return fig

    def attendance_summary_table(self):
        """
        Generate a summary table of attendance statistics.

        Returns:
            pd.DataFrame: Summary statistics per employee.
        """
        df = self.get_attendance_dataframe()
        emp_df = self.get_employee_dataframe()

        if df.empty:
            summary = emp_df.copy()
            summary["days_present"] = 0
            summary["last_present"] = None
            return summary[["employee_id", "name", "department", "days_present", "last_present"]]

        # Count days present per employee
        present_counts = df.groupby("employee_id").agg(
            days_present=("date", "count"),
            last_present=("date", "max"),
            avg_working_hours=("working_hours", "mean"),
        ).reset_index()

        summary = emp_df.merge(present_counts, on="employee_id", how="left")
        summary["days_present"] = summary["days_present"].fillna(0).astype(int)
        summary["last_present"] = summary["last_present"].fillna("Never")
        summary["avg_working_hours"] = summary["avg_working_hours"].round(2)

        return summary[["employee_id", "name", "department", "days_present", "avg_working_hours", "last_present"]]

    def working_hours_chart(self):
        """
        Generate a bar chart showing working hours per employee.

        Returns:
            plotly.graph_objects.Figure: A bar chart figure.
        """
        df = self.get_attendance_dataframe()

        if df.empty or "working_hours" not in df.columns:
            fig = go.Figure()
            fig.add_annotation(
                text="No working hours data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor="center", yanchor="middle",
                showarrow=False
            )
            fig.update_layout(title="Working Hours per Employee")
            return fig

        # Filter to records with working hours
        df_with_hours = df[df["working_hours"].notna()]

        if df_with_hours.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No check-out records available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor="center", yanchor="middle",
                showarrow=False
            )
            fig.update_layout(title="Working Hours per Employee")
            return fig

        # Group by employee and calculate average working hours
        hours_summary = df_with_hours.groupby(["employee_id", "name", "department"]).agg(
            avg_hours=("working_hours", "mean"),
            total_hours=("working_hours", "sum"),
            days_worked=("date", "count")
        ).reset_index()

        hours_summary = hours_summary.sort_values("avg_hours", ascending=False)

        fig = px.bar(
            hours_summary,
            x="name",
            y="avg_hours",
            color="department",
            title="Average Working Hours per Employee",
            labels={
                "name": "Employee Name",
                "avg_hours": "Average Working Hours",
                "department": "Department"
            },
            hover_data=["employee_id", "total_hours", "days_worked"],
        )
        fig.update_layout(xaxis_tickangle=-45, bargap=0.2)
        return fig

    def punctuality_chart(self):
        """
        Generate a pie chart showing punctuality distribution (Present, Late, Absent).

        Returns:
            plotly.graph_objects.Figure: A pie chart figure.
        """
        df = self.get_attendance_dataframe()

        if df.empty or "punctuality" not in df.columns:
            fig = go.Figure()
            fig.add_annotation(
                text="No punctuality data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor="center", yanchor="middle",
                showarrow=False
            )
            fig.update_layout(title="Punctuality Distribution")
            return fig

        # Count by punctuality status
        punctuality_counts = df["punctuality"].fillna("Present").value_counts().reset_index()
        punctuality_counts.columns = ["status", "count"]

        color_map = {
            "Present": "#28a745",
            "Late": "#ffc107",
            "Absent": "#dc3545"
        }

        fig = px.pie(
            punctuality_counts,
            values="count",
            names="status",
            title="Punctuality Distribution",
            color_discrete_map=color_map,
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        return fig

    def get_html_fig(self, fig):
        """
        Convert a Plotly figure to an HTML string for embedding in templates.

        Args:
            fig: A Plotly figure object.

        Returns:
            str: HTML string of the figure.
        """
        return fig.to_html(full_html=False, include_plotlyjs=True)


if __name__ == "__main__":
    analytics = AttendanceAnalytics()
    print("Analytics module initialized.")
    print(analytics.attendance_summary_table().head())