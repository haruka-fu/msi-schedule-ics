#!/usr/bin/env python3
"""
League The K4sen (LTK) Season Finale の試合スケジュールをICSファイルにまとめるスクリプト。

LTKは lolesports 公式APIには存在しない大会(ストリーマー大会)のため、
公式サイト/配信で発表されたスケジュール画像をもとに手動でデータを記述している。
日程が更新・確定したら DAY_MATCHES / PLAYOFF_DAYS を直接書き換えること。

試合開始時刻は原則アナウンスされていないため、終日イベントとして登録する。
時刻が判明した場合は build_vevents を終日(DATE)ではなく DTSTART/DTEND(DATETIME)に変更する。

使い方:
    python ltk_schedule_to_ics.py
"""

from datetime import date, timedelta

OUTPUT_FILE = "ltk_schedule.ics"
CALNAME = "LTK Season Finale Schedule"

TEAM_NAMES = {
    "DD": "Dahlia Diadem",
    "CC": "Camellia Crown",
    "IT": "Iris Tiara",
    "LR": "Laurel Regalia",
}

# レギュラーステージ: 日付 -> その日の対戦カード(チームcodeのペアのリスト)
REGULAR_STAGE = {
    "2026-10-15": [("CC", "DD"), ("IT", "LR")],
    "2026-10-19": [("CC", "LR"), ("DD", "IT")],
    "2026-10-23": [("LR", "DD"), ("IT", "CC")],
    "2026-10-27": [("LR", "IT"), ("DD", "CC")],
    "2026-11-02": [("IT", "DD"), ("LR", "CC")],
    "2026-11-06": [("CC", "IT"), ("DD", "LR")],
}

# マスターズカップ: 日付 -> その日の対戦カード
MASTERS_CUP = {
    "2026-10-20": [("DD", "CC"), ("IT", "LR")],
    "2026-10-28": [("DD", "IT"), ("CC", "LR")],
    "2026-11-09": [("DD", "LR"), ("CC", "IT")],
}

# プレイオフ: 対戦カード未発表のため日付のみ
PLAYOFF_DAYS = ["2026-11-21", "2026-11-22"]


def team_label(code):
    name = TEAM_NAMES.get(code, code)
    return f"{name}({code})"


def matchup_text(pairs):
    return ", ".join(f"{team_label(a)} vs {team_label(b)}" for a, b in pairs)


def build_allday_vevent(day_str, stage_key, summary, description):
    start = date.fromisoformat(day_str)
    end = start + timedelta(days=1)
    # 日付+ステージを基にした固定UID(毎回変わるとGit差分が無駄に発生するため)
    uid = f"{day_str}-{stage_key}@ltk-ics"
    return [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{start.strftime('%Y%m%dT000000Z')}",
        f"DTSTART;VALUE=DATE:{start.strftime('%Y%m%d')}",
        f"DTEND;VALUE=DATE:{end.strftime('%Y%m%d')}",
        f"SUMMARY:{summary}",
        f"DESCRIPTION:{description}",
        "END:VEVENT",
    ]


def build_vevents():
    lines = []

    for day_str, pairs in sorted(REGULAR_STAGE.items()):
        summary = "[LTK Finale] レギュラーステージ"
        description = f"Regular Stage\\n{matchup_text(pairs)}"
        lines += build_allday_vevent(day_str, "regular", summary, description)

    for day_str, pairs in sorted(MASTERS_CUP.items()):
        summary = "[LTK Finale] マスターズカップ"
        description = f"Masters Cup\\n{matchup_text(pairs)}"
        lines += build_allday_vevent(day_str, "masters", summary, description)

    for day_str in sorted(PLAYOFF_DAYS):
        summary = "[LTK Finale] プレイオフ"
        description = "Playoffs(対戦カード未発表)"
        lines += build_allday_vevent(day_str, "playoffs", summary, description)

    return lines


def main():
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//self-made//ltk-ics//JA",
        f"X-WR-CALNAME:{CALNAME}",
    ]
    lines += build_vevents()
    lines.append("END:VCALENDAR")

    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as f:
        f.write("\r\n".join(lines))
    print(f"{OUTPUT_FILE} を生成しました")


if __name__ == "__main__":
    main()
