#!/usr/bin/env python3
"""
正規化済みイベント一覧(lol_esports_to_ics.build_event_dictsの出力)を
Google Calendar APIで直接カレンダーに反映するモジュール。

認証にはOAuthのリフレッシュトークンを使う(取得方法はREADME参照)。
以下の環境変数が必要:
    GOOGLE_CLIENT_ID
    GOOGLE_CLIENT_SECRET
    GOOGLE_REFRESH_TOKEN

書き込み先カレンダーは CALENDAR_SUMMARY で指定した名前のカレンダーを
自動で探し、無ければ新規作成する(カレンダーIDをsecretで管理する必要がない)。

このモジュールが作成・更新するイベントには extendedProperties.private に
目印(SOURCE_TAG)を付与し、それ以外の(ユーザーが手動追加した)イベントは
一覧取得・削除の対象から除外する。
"""

import os
import time

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

CALENDAR_SUMMARY = "LoL Esports Schedule"
SOURCE_TAG = "lolesports-ics"
TOKEN_URI = "https://oauth2.googleapis.com/token"

# insert/update/delete の書き込み系呼び出しを連続で投げるとGoogle Calendar APIの
# バースト制限(rateLimitExceeded)に引っかかるため、1件ごとに間隔を空ける。
WRITE_INTERVAL_SECONDS = 0.3


def _build_service():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        token_uri=TOKEN_URI,
        scopes=["https://www.googleapis.com/auth/calendar"],
    )
    return build("calendar", "v3", credentials=creds)


def _ensure_calendar(service):
    page_token = None
    while True:
        result = service.calendarList().list(pageToken=page_token).execute()
        for cal in result.get("items", []):
            if cal.get("summary") == CALENDAR_SUMMARY:
                return cal["id"]
        page_token = result.get("nextPageToken")
        if not page_token:
            break

    created = service.calendars().insert(
        body={"summary": CALENDAR_SUMMARY, "timeZone": "Asia/Tokyo"}
    ).execute()
    print(f"カレンダー「{CALENDAR_SUMMARY}」を新規作成しました (id={created['id']})")
    return created["id"]


def _event_id(uid):
    # Google Calendarのイベントidは [a-v0-9]{5,1024} である必要がある。
    # uidは "<matchId>@lolesports-ics" という数字主体の文字列なので、
    # 区切り文字を取り除くだけで条件を満たせる。
    cleaned = "".join(ch for ch in uid.lower() if ch in "0123456789abcdefghijklmnopqrstuv")
    return ("e" + cleaned)[:1024]


def _list_managed_events(service, calendar_id):
    managed = {}
    page_token = None
    while True:
        result = (
            service.events()
            .list(
                calendarId=calendar_id,
                privateExtendedProperty=f"source={SOURCE_TAG}",
                showDeleted=False,
                singleEvents=True,
                pageToken=page_token,
                maxResults=2500,
            )
            .execute()
        )
        for item in result.get("items", []):
            managed[item["id"]] = item
        page_token = result.get("nextPageToken")
        if not page_token:
            break
    return managed


def sync_events(event_dicts):
    service = _build_service()
    calendar_id = _ensure_calendar(service)

    existing = _list_managed_events(service, calendar_id)

    desired_ids = set()
    created, updated, unchanged = 0, 0, 0

    for ev in event_dicts:
        event_id = _event_id(ev["uid"])
        desired_ids.add(event_id)

        body = {
            "id": event_id,
            "summary": ev["summary"],
            "description": ev["description"].replace("\\n", "\n"),
            "start": {"dateTime": ev["start"].isoformat()},
            "end": {"dateTime": ev["end"].isoformat()},
            "extendedProperties": {"private": {"source": SOURCE_TAG}},
        }

        current = existing.get(event_id)
        if current is None:
            try:
                service.events().insert(calendarId=calendar_id, body=body).execute()
                created += 1
            except HttpError as e:
                if e.resp.status == 409:
                    service.events().update(
                        calendarId=calendar_id, eventId=event_id, body=body
                    ).execute()
                    updated += 1
                else:
                    raise
            time.sleep(WRITE_INTERVAL_SECONDS)
        else:
            if (
                current.get("summary") == body["summary"]
                and current.get("description") == body["description"]
                and current.get("start", {}).get("dateTime", "")[:19]
                == body["start"]["dateTime"][:19]
                and current.get("end", {}).get("dateTime", "")[:19]
                == body["end"]["dateTime"][:19]
            ):
                unchanged += 1
            else:
                service.events().update(
                    calendarId=calendar_id, eventId=event_id, body=body
                ).execute()
                updated += 1
                time.sleep(WRITE_INTERVAL_SECONDS)

    deleted = 0
    for stale_id in set(existing) - desired_ids:
        service.events().delete(calendarId=calendar_id, eventId=stale_id).execute()
        deleted += 1
        time.sleep(WRITE_INTERVAL_SECONDS)

    print(
        f"Googleカレンダー同期完了: 新規{created}件 / 更新{updated}件 / "
        f"変更なし{unchanged}件 / 削除{deleted}件"
    )
