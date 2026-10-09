"""Google Workspace integration layer (Gmail, Calendar, Drive, Docs, Sheets, Slides).

Uses OAuth 2.0 with least-privilege scopes. Tokens stored securely.
Each service client is lazy-loaded and handles token refresh automatically.
"""

import json
import os
import time
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional

import logging

from Brain.logger import get_logger

logger = get_logger(__name__)

# Least-privilege scopes per service
SCOPES = {
    "gmail": [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.modify",
    ],
    "calendar": [
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/calendar.events",
    ],
    "drive": [
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive.readonly",
    ],
    "docs": [
        "https://www.googleapis.com/auth/documents",
        "https://www.googleapis.com/auth/drive.file",
    ],
    "sheets": [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
    ],
    "slides": [
        "https://www.googleapis.com/auth/presentations",
        "https://www.googleapis.com/auth/drive.file",
    ],
    "tasks": [
        "https://www.googleapis.com/auth/tasks",
    ],
}

DEFAULT_TOKEN_DIR = Path.home() / ".astra" / "google_tokens"
DEFAULT_CREDS_FILE = Path.home() / ".astra" / "google_credentials.json"


class TokenStore:
    """Secure token persistence with JSON serialization (no pickle)."""

    def __init__(self, token_dir: Path = DEFAULT_TOKEN_DIR):
        self.token_dir = Path(token_dir)
        self.token_dir.mkdir(parents=True, exist_ok=True)

    def _token_path(self, service: str) -> Path:
        return self.token_dir / f"{service}_token.json"

    def save(self, service: str, credentials) -> None:
        path = self._token_path(service)
        data = {
            "token": getattr(credentials, "token", None),
            "refresh_token": getattr(credentials, "refresh_token", None),
            "token_uri": getattr(credentials, "token_uri", None),
            "client_id": getattr(credentials, "client_id", None),
            "client_secret": getattr(credentials, "client_secret", None),
            "scopes": list(getattr(credentials, "scopes", []) or []),
            "expiry": getattr(credentials, "expiry", None).isoformat() if getattr(credentials, "expiry", None) else None,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.chmod(path, 0o600)

    def load(self, service: str):
        path = self._token_path(service)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        from google.oauth2.credentials import Credentials
        return Credentials(
            token=data.get("token"),
            refresh_token=data.get("refresh_token"),
            token_uri=data.get("token_uri"),
            client_id=data.get("client_id"),
            client_secret=data.get("client_secret"),
            scopes=data.get("scopes", []),
        )

    def delete(self, service: str) -> None:
        path = self._token_path(service)
        if path.exists():
            path.unlink()


class GoogleWorkspaceClient:
    """Base client with auth handling."""

    def __init__(
        self,
        service_name: str,
        api_name: str,
        api_version: str,
        scopes: List[str],
        token_store: Optional["TokenStore"] = None,
        creds_file: Path = DEFAULT_CREDS_FILE,
    ):
        self.service_name = service_name
        self.api_name = api_name
        self.api_version = api_version
        self.scopes = scopes
        self.token_store = token_store or TokenStore()
        self.creds_file = Path(creds_file)
        self._service = None
        self._credentials = None

    def _load_credentials(self):
        """Load or refresh credentials."""
        if self._credentials and self._credentials.valid:
            return self._credentials

        # Try loading saved token
        self._credentials = self.token_store.load(self.service_name)

        if self._credentials and self._credentials.expired and self._credentials.refresh_token:
            from google.auth.transport.requests import Request
            self._credentials.refresh(Request())
            self.token_store.save(self.service_name, self._credentials)
            return self._credentials

        # Need fresh OAuth flow
        if not self.creds_file.exists():
            raise RuntimeError(
                f"Google credentials not found at {self.creds_file}. "
                "Run setup_google.py to configure."
            )

        from google_auth_oauthlib.flow import InstalledAppFlow
        flow = InstalledAppFlow.from_client_secrets_file(
            str(self.creds_file), self.scopes
        )
        self._credentials = flow.run_local_server(port=0)
        self.token_store.save(self.service_name, self._credentials)
        return self._credentials

    def _get_service(self):
        if self._service is None:
            from googleapiclient.discovery import build
            creds = self._load_credentials()
            self._service = build(self.api_name, self.api_version, credentials=creds)
        return self._service


class GmailClient(GoogleWorkspaceClient):
    """Gmail API wrapper."""

    def __init__(self, **kwargs):
        super().__init__("gmail", "gmail", "v1", SCOPES["gmail"], **kwargs)

    def search_messages(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search messages and return list of message metadata."""
        service = self._get_service()
        results = service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()
        messages = results.get("messages", [])
        detailed = []
        for msg in messages:
            detail = service.users().messages().get(
                userId="me", id=msg["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"]
            ).execute()
            headers = {h["name"]: h["value"] for h in detail.get("payload", {}).get("headers", [])}
            detailed.append({
                "id": msg["id"],
                "thread_id": msg.get("threadId"),
                "from": headers.get("From", ""),
                "subject": headers.get("Subject", ""),
                "date": headers.get("Date", ""),
            })
        return detailed

    def read_message(self, message_id: str) -> Dict:
        """Read full message content."""
        service = self._get_service()
        msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()
        payload = msg.get("payload", {})
        headers = {h["name"]: h["value"] for h in payload.get("headers", [])}

        body = ""
        if "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain":
                    import base64
                    data = part.get("body", {}).get("data", "")
                    if data:
                        body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                        break
        elif payload.get("mimeType") == "text/plain":
            import base64
            data = payload.get("body", {}).get("data", "")
            if data:
                body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

        return {
            "id": msg["id"],
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "subject": headers.get("Subject", ""),
            "date": headers.get("Date", ""),
            "body": body,
        }

    def create_draft(self, to: str, subject: str, body: str) -> Dict:
        """Create a draft email."""
        import base64
        from email.mime.text import MIMEText

        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        service = self._get_service()
        draft = service.users().drafts().create(
            userId="me", body={"message": {"raw": raw}}
        ).execute()
        return draft

    def send_message(self, to: str, subject: str, body: str) -> Dict:
        """Send an email directly."""
        import base64
        from email.mime.text import MIMEText

        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        service = self._get_service()
        sent = service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()
        return sent


class CalendarClient(GoogleWorkspaceClient):
    """Google Calendar API wrapper."""

    def __init__(self, **kwargs):
        super().__init__("calendar", "calendar", "v3", SCOPES["calendar"], **kwargs)

    def list_events(
        self, time_min: Optional[str] = None, time_max: Optional[str] = None, max_results: int = 20
    ) -> List[Dict]:
        service = self._get_service()
        events_result = service.events().list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        events = events_result.get("items", [])
        return [
            {
                "id": e["id"],
                "summary": e.get("summary", ""),
                "start": e["start"].get("dateTime", e["start"].get("date")),
                "end": e["end"].get("dateTime", e["end"].get("date")),
                "location": e.get("location", ""),
                "attendees": [a.get("email", "") for a in e.get("attendees", [])],
            }
            for e in events
        ]

    def create_event(
        self,
        summary: str,
        start_time: str,
        end_time: Optional[str] = None,
        description: str = "",
        location: str = "",
        attendees: Optional[List[str]] = None,
    ) -> Dict:
        service = self._get_service()
        event = {
            "summary": summary,
            "description": description,
            "location": location,
            "start": {"dateTime": start_time, "timeZone": "Asia/Ho_Chi_Minh"},
            "end": {"dateTime": end_time or start_time, "timeZone": "Asia/Ho_Chi_Minh"},
            "attendees": [{"email": a} for a in (attendees or [])],
            "reminders": {"useDefault": True},
        }
        created = service.events().insert(calendarId="primary", body=event).execute()
        return {
            "id": created["id"],
            "html_link": created.get("htmlLink"),
            "status": created.get("status"),
        }

    def update_event(self, event_id: str, **updates) -> Dict:
        service = self._get_service()
        event = service.events().get(calendarId="primary", eventId=event_id).execute()
        event.update(updates)
        updated = service.events().update(calendarId="primary", eventId=event_id, body=event).execute()
        return updated

    def delete_event(self, event_id: str) -> bool:
        service = self._get_service()
        service.events().delete(calendarId="primary", eventId=event_id).execute()
        return True


class DriveClient(GoogleWorkspaceClient):
    """Google Drive API wrapper."""

    def __init__(self, **kwargs):
        super().__init__("drive", "drive", "v3", SCOPES["drive"], **kwargs)

    def search_files(self, query: str, max_results: int = 20) -> List[Dict]:
        service = self._get_service()
        results = service.files().list(
            q=query, pageSize=max_results, fields="files(id,name,mimeType,modifiedTime,webViewLink)"
        ).execute()
        return results.get("files", [])

    def upload_file(self, file_path: str, folder_id: Optional[str] = None) -> Dict:
        from googleapiclient.http import MediaFileUpload
        service = self._get_service()
        file_name = os.path.basename(file_path)
        media = MediaFileUpload(file_path, resumable=True)
        body = {"name": file_name}
        if folder_id:
            body["parents"] = [folder_id]
        file = service.files().create(body=body, media_body=media, fields="id,name,webViewLink").execute()
        return file

    def download_file(self, file_id: str, destination: str) -> bool:
        service = self._get_service()
        request = service.files().get_media(fileId=file_id)
        with open(destination, "wb") as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
        return True


class DocsClient(GoogleWorkspaceClient):
    """Google Docs API wrapper."""

    def __init__(self, **kwargs):
        super().__init__("docs", "docs", "v1", SCOPES["docs"], **kwargs)

    def create_document(self, title: str, content: str = "") -> Dict:
        service = self._get_service()
        doc = service.documents().create(body={"title": title}).execute()
        doc_id = doc["documentId"]
        if content:
            self.append_text(doc_id, content)
        return {"documentId": doc_id, "title": title}

    def append_text(self, document_id: str, text: str) -> None:
        service = self._get_service()
        requests = [{
            "insertText": {
                "location": {"index": 1},
                "text": text
            }
        }]
        service.documents().batchUpdate(documentId=document_id, body={"requests": requests}).execute()

    def read_document(self, document_id: str) -> str:
        service = self._get_service()
        doc = service.documents().get(documentId=document_id).execute()
        content = ""
        for element in doc.get("body", {}).get("content", []):
            if "paragraph" in element:
                for elem in element["paragraph"].get("elements", []):
                    if "textRun" in elem:
                        content += elem["textRun"].get("content", "")
        return content


class SheetsClient(GoogleWorkspaceClient):
    """Google Sheets API wrapper."""

    def __init__(self, **kwargs):
        super().__init__("sheets", "sheets", "v4", SCOPES["sheets"], **kwargs)

    def create_spreadsheet(self, title: str, rows: List[List] = None) -> Dict:
        service = self._get_service()
        body = {"properties": {"title": title}}
        if rows:
            body["sheets"] = [{"data": [{"rowData": [{"values": [{"userEnteredValue": {"stringValue": str(c)}} for c in r]} for r in rows]}]}]
        spreadsheet = service.spreadsheets().create(body=body, fields="spreadsheetId").execute()
        return {"spreadsheetId": spreadsheet["spreadsheetId"], "title": title}

    def append_rows(self, spreadsheet_id: str, rows: List[List], range_name: str = "A1") -> None:
        service = self._get_service()
        values = [{"values": row} for row in rows]
        body = {"values": [[str(c) for c in row] for row in rows]}
        service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id, range=range_name,
            valueInputOption="USER_ENTERED", body=body
        ).execute()

    def read_range(self, spreadsheet_id: str, range_name: str) -> List[List]:
        service = self._get_service()
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=range_name
        ).execute()
        return result.get("values", [])


class SlidesClient(GoogleWorkspaceClient):
    """Google Slides API wrapper."""

    def __init__(self, **kwargs):
        super().__init__("slides", "slides", "v1", SCOPES["slides"], **kwargs)

    def create_presentation(self, title: str, content: str = "") -> Dict:
        service = self._get_service()
        presentation = service.presentations().create(body={"title": title}).execute()
        pres_id = presentation["presentationId"]
        if content:
            # Add content to first slide
            requests = [{
                "createSlide": {
                    "objectId": "slide1",
                    "insertionIndex": "1",
                    "slideLayoutReference": {"predefinedLayout": "TITLE_AND_BODY"}
                }
            }]
            service.presentations().batchUpdate(
                presentationId=pres_id, body={"requests": requests}
            ).execute()
        return {"presentationId": pres_id, "title": title}


class TasksClient(GoogleWorkspaceClient):
    """Google Tasks API wrapper."""

    def __init__(self, **kwargs):
        super().__init__("tasks", "tasks", "v1", SCOPES["tasks"], **kwargs)

    def list_tasklists(self) -> List[Dict]:
        service = self._get_service()
        result = service.tasklists().list().execute()
        return result.get("items", [])

    def create_task(self, tasklist: str, title: str, notes: str = "", due: Optional[str] = None) -> Dict:
        service = self._get_service()
        body = {"title": title, "notes": notes}
        if due:
            body["due"] = due
        task = service.tasks().insert(tasklist=tasklist, body=body).execute()
        return task

    def list_tasks(self, tasklist: str) -> List[Dict]:
        service = self._get_service()
        result = service.tasks().list(tasklist=tasklist).execute()
        return result.get("items", [])


class GoogleWorkspaceManager:
    """Unified manager for all Google Workspace services."""

    def __init__(
        self,
        token_dir: Path = DEFAULT_TOKEN_DIR,
        creds_file: Path = DEFAULT_CREDS_FILE,
    ):
        self.token_store = TokenStore(token_dir)
        self.creds_file = Path(creds_file)
        self._clients = {}

    def _get_client(self, client_class):
        name = client_class.__name__.lower().replace("client", "")
        if name not in self._clients:
            self._clients[name] = client_class(
                token_store=self.token_store, creds_file=self.creds_file
            )
        return self._clients[name]

    @property
    def gmail(self) -> GmailClient:
        return self._get_client(GmailClient)

    @property
    def calendar(self) -> CalendarClient:
        return self._get_client(CalendarClient)

    @property
    def drive(self) -> DriveClient:
        return self._get_client(DriveClient)

    @property
    def docs(self) -> DocsClient:
        return self._get_client(DocsClient)

    @property
    def sheets(self) -> SheetsClient:
        return self._get_client(SheetsClient)

    @property
    def slides(self) -> SlidesClient:
        return self._get_client(SlidesClient)

    @property
    def tasks(self) -> TasksClient:
        return self._get_client(TasksClient)

    def check_auth(self) -> Dict[str, bool]:
        """Check which services are authenticated."""
        status = {}
        for name in ["gmail", "calendar", "drive", "docs", "sheets", "slides", "tasks"]:
            token_path = DEFAULT_TOKEN_DIR / f"{name}_token.pickle"
            status[name] = token_path.exists()
        return status

    def disconnect(self, service: str) -> None:
        """Revoke access for a service."""
        self.token_store.delete(service)
        if service in self._clients:
            del self._clients[service]