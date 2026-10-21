import calendar
from datetime import date, timedelta


def add_months(day: date, months: int) -> date:
    """Same day of month `months` later, clamped to the month's last day."""
    index = day.month - 1 + months
    year, month = day.year + index // 12, index % 12 + 1
    return day.replace(
        year=year, month=month, day=min(day.day, calendar.monthrange(year, month)[1])
    )


def week_start(day: date) -> date:
    """Monday of the ISO week holding `day`."""
    return day - timedelta(days=day.weekday())
