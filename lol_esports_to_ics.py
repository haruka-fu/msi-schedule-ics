#!/usr/bin/env python3
"""
League of Legends の国際大会(MSI, Worlds, First Stand)の試合スケジュールを
lolesports公式の非公開APIから取得し、まとめて1つのICSファイルを生成するスクリプト。

使い方:
    pip install -r requirements.txt
    python msi_to_ics.py

生成された all_leagues_schedule.ics は、GitHub Actions で定期実行して
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

OUTPUT_FILE = "all_leagues_schedule.ics"

# 対象大会のslug(getLeaguesで取得できる一意な識別子)
TARGET_LEAGUE_SLUGS = ["msi", "worlds", "first_stand"]


def get_leagues():
    """全リーグ一覧から対象大会のリーグID/名前を集める"""
    r = requests.get(f"{BASE}/getLeagues", headers=HEADERS, params={"hl": "ja-JP"})
    r.raise_for_status()
    leagues = r.json()["data"]["leagues"]

    found = []
    found_slugs = set()
    for lg in leagues:
        if lg["slug"] in TARGET_LEAGUE_SLUGS:
            found.append((lg["id"], lg["name"]))
            found_slugs.add(lg["slug"])

    missing = set(TARGET_LEAGUE_SLUGS) - found_slugs
    if missing:
        raise RuntimeError(f"次の大会が見つかりませんでした: {missing}")
    return found


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


def build_vevents(events, league_name):
    lines = []

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
        summary = f"[{league_name}] " + (
            " vs ".join(team_names) if team_names else "Match"
        )

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

        uid = f"{match.get('id', uuid.uuid4())}@lolesports-ics"

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

    return lines


def main():
    leagues = get_leagues()

    all_vevents = []
    for league_id, league_name in leagues:
        print(f"League found: {league_name} (id={league_id})")
        events = get_all_schedule_events(league_id)
        print(f"  {len(events)} 件のイベントを取得しました")
        all_vevents += build_vevents(events, league_name)

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//self-made//lolesports-ics//JA",
        "X-WR-CALNAME:LoL International Events Schedule",
    ]
    lines += all_vevents
    lines.append("END:VCALENDAR")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\r\n".join(lines))
    print(f"{OUTPUT_FILE} を生成しました")


if __name__ == "__main__":
    main()
