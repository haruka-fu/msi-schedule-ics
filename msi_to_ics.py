#!/usr/bin/env python3
"""
MSI (Mid-Season Invitational) の試合スケジュールを
lolesports公式の非公開APIから取得し、ICSファイルを生成するスクリプト。

使い方:
    pip install -r requirements.txt
    python msi_to_ics.py

生成された msi_schedule.ics は、GitHub Actions で定期実行して
リポジトリにコミットすることで自動更新されます。Google カレンダー側は
その raw ファイルの URL を「他のカレンダー > URLで追加」で購読してください。
"""

import os
import requests
from datetime import datetime, timedelta, timezone
import uuid

# 環境変数 LOLESPORTS_API_KEY が設定されていればそちらを優先します。
API_KEY = os.environ.get("LOLESPORTS_API_KEY", "0TvQnueqKa5mxJntVWt0w4LpLfEkrV1Ta8rQBb9Z")
BASE = "https://esports-api.lolesports.com/persisted/gw"
HEADERS = {"x-api-key": API_KEY}

# 対象リーグ名に含まれるキーワード(大文字小文字無視)
LEAGUE_NAME_HINT = "MSI"


def get_league_id():
    """全リーグ一覧から MSI のリーグIDを探す"""
    r = requests.get(f"{BASE}/getLeagues", headers=HEADERS, params={"hl": "ja-JP"})
    r.raise_for_status()
    leagues = r.json()["data"]["leagues"]
    for lg in leagues:
        if LEAGUE_NAME_HINT.lower() in lg["name"].lower() or lg["slug"] == "msi":
            return lg["id"], lg["name"]
    raise RuntimeError("MSIリーグが見つかりませんでした。getLeaguesの結果を確認してください。")


def get_all_schedule_events(league_id):
    """ページングしながら該当リーグの全試合イベントを収集する"""
    events = []
    seen_tokens = set()

    def fetch(page_token=None):
        params = {"hl": "ja-JP", "leagueId": league_id}
        if page_token:
            params["pageToken"] = page_token
        r = requests.get(f"{BASE}/getSchedule", headers=HEADERS, params=params)
        r.raise_for_status()
        return r.json()["data"]["schedule"]

    # 現在を中心にしたページを取得
    schedule = fetch()
    events.extend(schedule["events"])

    # 過去方向にページング
    token = schedule.get("pages", {}).get("older")
    while token and token not in seen_tokens:
        seen_tokens.add(token)
        schedule = fetch(token)
        new_events = schedule["events"]
        if not new_events:
            break
        events.extend(new_events)
        token = schedule.get("pages", {}).get("older")

    # 未来方向にページング
    schedule = fetch()
    token = schedule.get("pages", {}).get("newer")
    while token and token not in seen_tokens:
        seen_tokens.add(token)
        schedule = fetch(token)
        new_events = schedule["events"]
        if not new_events:
            break
        events.extend(new_events)
        token = schedule.get("pages", {}).get("newer")

    # 重複除去 (matchId基準)
    unique = {}
    for ev in events:
        match = ev.get("match")
        key = match["id"] if match else ev.get("id", str(ev))
        unique[key] = ev
    return list(unique.values())


def estimate_duration_minutes(best_of):
    # Bo5なら長め、Bo1なら短めに見積もる(あくまで目安)
    return {1: 60, 3: 120, 5: 180}.get(best_of, 120)


def build_ics(events, league_name):
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//self-made//lolesports-msi-ics//JA",
        f"X-WR-CALNAME:{league_name} Schedule",
    ]

    for ev in events:
        match = ev.get("match")
        if not match:
            continue  # show形式などmatch以外のイベントはスキップ

        start_str = ev["startTime"]  # 例: 2026-07-03T03:00:00Z
        start_dt = datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )

        teams = match.get("teams", [])
        # 略称(code)を優先。無ければ正式名、それも無ければTBD
        team_names = [t.get("code") or t.get("name") or "TBD" for t in teams]
        summary = " vs ".join(team_names) if team_names else "MSI Match"

        strategy = match.get("strategy", {})
        best_of = strategy.get("count", 3)
        duration = estimate_duration_minutes(best_of)
        end_dt = start_dt + timedelta(minutes=duration)

        full_names = [t.get("name") or t.get("code") or "TBD" for t in teams]
        stage_name = ev.get("blockName", "")
        description = (
            f"{league_name} - {stage_name} (Bo{best_of})\\n"
            f"{' vs '.join(full_names)}"
        )

        uid = f"{match.get('id', uuid.uuid4())}@msi-ics"

        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART:{start_dt.strftime('%Y%m%dT%H%M%SZ')}",
            f"DTEND:{end_dt.strftime('%Y%m%dT%H%M%SZ')}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{description}",
            "END:VEVENT",
        ]

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


def main():
    league_id, league_name = get_league_id()
    print(f"League found: {league_name} (id={league_id})")

    events = get_all_schedule_events(league_id)
    print(f"{len(events)} 件のイベントを取得しました")

    ics_text = build_ics(events, league_name)
    with open("msi_schedule.ics", "w", encoding="utf-8") as f:
        f.write(ics_text)
    print("msi_schedule.ics を生成しました")


if __name__ == "__main__":
    main()
