from datetime import datetime, time, date
from zoneinfo import ZoneInfo

from google.oauth2 import service_account
from googleapiclient.discovery import build

SERVICE_ACCOUNT_FILE = 'google-calendar-service-account.json.secret'
SCOPES = ['https://www.googleapis.com/auth/calendar']
TIMEZONE = ZoneInfo('Europe/Berlin')


class GoogleCalendar:

    def __init__(self, calendar_id: str) -> None:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=SCOPES
        )
        self._service = build('calendar', 'v3', credentials=credentials)
        self._calendar_id = calendar_id

    def is_correctly_configured(self) -> bool:
        return self._calendar_id is not None

    def fetch_blocker_events(self, lookup_date: date) -> list[dict]:
        def user_is_organizer(event: dict) -> bool:
            return event.get("organizer", {}).get("self", False)

        def user_has_accepted(event: dict) -> bool:
            return any(
                attendee.get("self") and attendee.get("responseStatus") == "accepted"
                for attendee in event.get("attendees", [])
            )

        print(f"[GoogleCalendar] Fetching blocker events at {lookup_date} from calendar {self._calendar_id}.")

        # https://developers.google.com/workspace/calendar/api/v3/reference/events/list
        events_result = self._service.events().list(
            calendarId=self._calendar_id,
            eventTypes=["default", "focusTime", "fromGmail", "outOfOffice"],
            timeMin=datetime.combine(lookup_date, time.min, tzinfo=TIMEZONE).isoformat(timespec="seconds"),
            timeMax=datetime.combine(lookup_date, time.max, tzinfo=TIMEZONE).isoformat(timespec="seconds"),
            timeZone=TIMEZONE.key,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        blocker_events = [
            event for event in events_result.get("items", [])
            if user_is_organizer(event) or user_has_accepted(event)
        ]

        print(f"[GoogleCalendar] Fetched {len(blocker_events)} blocker events.")

        return blocker_events

    def create_event(
            self,
            title: str,
            start_datetime: datetime,
            end_datetime: datetime,
            participants_emails: list[str]
    ) -> str:
        if start_datetime.tzinfo is None:
            start_datetime = start_datetime.replace(tzinfo=TIMEZONE)
        if end_datetime.tzinfo is None:
            end_datetime = end_datetime.replace(tzinfo=TIMEZONE)
        event = {
            'summary': title,
            'description': 'Created by QArrange.',
            'start': {
                'dateTime': start_datetime.isoformat(timespec="seconds"),
            },
            'end': {
                'dateTime': end_datetime.isoformat(timespec="seconds"),
            },
            # TODO: Disabled for now, requires domain-wide delegation enabled for service account
            # 'attendees': [{'email': email} for email in participants_emails]
        }

        print(f"[GoogleCalendar] Creating event in calendar {self._calendar_id}: {event}")

        # https://developers.google.com/workspace/calendar/api/v3/reference/events/insert
        created_event = self._service.events().insert(
            calendarId=self._calendar_id,
            body=event,
            sendUpdates='all'
        ).execute()

        print(f"[GoogleCalendar] Created event: {created_event.get('htmlLink')}")

        return created_event.get('htmlLink')
