#!/usr/bin/env python3
"""YouTube Data API v3로 채널 전체 업로드 목록 수집.

API 키는 환경변수 YT_API_KEY 로만 전달합니다. 절대 커밋하지 마세요.

사용법:
    export YT_API_KEY="..."
    python3 tools/yt_fetch.py --channel UC-SDn1Rid0XP06ovSQwLnZg -o content/alphamale_videos.json
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

API = "https://www.googleapis.com/youtube/v3"


def call(endpoint, key, **params):
    params["key"] = key
    url = f"{API}/{endpoint}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        print(f"HTTP {e.code} on {endpoint}: {body[:500]}", file=sys.stderr)
        raise


def uploads_playlist(channel_id, key):
    d = call("channels", key, part="contentDetails,snippet,statistics", id=channel_id)
    if not d.get("items"):
        raise SystemExit(f"채널을 찾을 수 없습니다: {channel_id}")
    it = d["items"][0]
    return (
        it["contentDetails"]["relatedPlaylists"]["uploads"],
        it["snippet"]["title"],
        it["statistics"],
    )


def all_video_ids(playlist_id, key):
    ids, token = [], None
    while True:
        d = call("playlistItems", key, part="contentDetails",
                 playlistId=playlist_id, maxResults=50,
                 **({"pageToken": token} if token else {}))
        ids += [i["contentDetails"]["videoId"] for i in d.get("items", [])]
        token = d.get("nextPageToken")
        if not token:
            return ids


def video_details(ids, key):
    out = []
    for i in range(0, len(ids), 50):
        chunk = ids[i:i + 50]
        d = call("videos", key, part="snippet,statistics,contentDetails",
                 id=",".join(chunk))
        for v in d.get("items", []):
            s, st = v["snippet"], v.get("statistics", {})
            out.append({
                "id": v["id"],
                "title": s["title"],
                "published": s["publishedAt"],
                "views": int(st.get("viewCount", 0)),
                "likes": int(st.get("likeCount", 0)),
                "comments": int(st.get("commentCount", 0)),
                "duration": v["contentDetails"]["duration"],
                "description": s.get("description", ""),
                "tags": s.get("tags", []),
            })
        print(f"  ... {len(out)}/{len(ids)}", file=sys.stderr)
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--channel", required=True)
    p.add_argument("-o", "--out", required=True)
    a = p.parse_args()

    key = os.environ.get("YT_API_KEY")
    if not key:
        raise SystemExit("환경변수 YT_API_KEY 가 필요합니다.")

    pl, title, stats = uploads_playlist(a.channel, key)
    print(f"채널: {title}", file=sys.stderr)
    print(f"구독자 {int(stats.get('subscriberCount',0)):,} / "
          f"영상 {int(stats.get('videoCount',0)):,} / "
          f"총조회 {int(stats.get('viewCount',0)):,}", file=sys.stderr)

    ids = all_video_ids(pl, key)
    print(f"업로드 {len(ids)}개 수집 중...", file=sys.stderr)
    vids = video_details(ids, key)
    vids.sort(key=lambda v: v["views"], reverse=True)

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump({"channel": title, "stats": stats, "videos": vids},
                  f, ensure_ascii=False, indent=2)
    print(f"저장: {a.out} ({len(vids)}편)", file=sys.stderr)


if __name__ == "__main__":
    main()
