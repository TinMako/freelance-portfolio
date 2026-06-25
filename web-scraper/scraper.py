"""quotes.toscrape.com スクレイパー（ポートフォリオ用）。

許可された練習用サイト http://quotes.toscrape.com から
引用文・著者・タグを収集し、構造化 CSV として出力する。

設計方針:
- robots.txt を urllib.robotparser で事前確認し、禁止されていれば停止する
  （順守の習慣化。当該サイトは robots.txt 不在＝全許可だが、実案件を想定して必ず確認する）。
- ページ間に礼儀的な待機（DELAY 秒）を入れ、サーバへ負荷をかけない。
- ネットワーク異常・HTML 構造変化は握り潰さず例外として顕在化させる。

AI（Tatara）が自律生成したコードです。詳細は README.md を参照。
"""

from __future__ import annotations

import csv
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://quotes.toscrape.com"
START_PATH = "/"
USER_AGENT = "TataraPortfolioBot/1.0 (+educational scraping demo; respects robots.txt)"
REQUEST_TIMEOUT = 15  # 秒
POLITE_DELAY = 1.0  # ページ間の待機秒数（サーバ負荷軽減）


@dataclass(frozen=True)
class Quote:
    """1 件の引用文レコード（イミュータブル）。"""

    text: str
    author: str
    tags: str  # パイプ区切り。CSV で扱いやすい単純表現にする


def is_allowed(base_url: str, path: str, user_agent: str) -> bool:
    """robots.txt を取得し、対象パスのクロールが許可されているか判定する。

    robots.txt が存在しない（404 等で読めない）場合は「制限なし」とみなす。
    これは Robots Exclusion Protocol の標準的解釈に従う。
    """
    parser = RobotFileParser()
    robots_url = urljoin(base_url, "/robots.txt")
    try:
        resp = requests.get(robots_url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": user_agent})
        if resp.status_code == 200:
            parser.parse(resp.text.splitlines())
            return parser.can_fetch(user_agent, urljoin(base_url, path))
        # robots.txt が無い → 制限なしとして許可
        return True
    except requests.RequestException as exc:  # noqa: BLE001 - ネットワーク異常は明示ログ
        print(f"[warn] robots.txt 取得失敗 ({exc}); 制限なしとして続行", file=sys.stderr)
        return True


def parse_quotes(html: str) -> list[Quote]:
    """1 ページ分の HTML から引用文レコードを抽出する。"""
    soup = BeautifulSoup(html, "html.parser")
    quotes: list[Quote] = []
    for block in soup.select("div.quote"):
        text_el = block.select_one("span.text")
        author_el = block.select_one("small.author")
        if text_el is None or author_el is None:
            # 構造が想定外 → 握り潰さず可視化（HTML 変化の早期検知）
            raise ValueError("想定した .quote 構造が見つかりません（サイト構造が変化した可能性）")
        tags = [t.get_text(strip=True) for t in block.select("a.tag")]
        quotes.append(
            Quote(
                text=text_el.get_text(strip=True).strip("“”"),
                author=author_el.get_text(strip=True),
                tags="|".join(tags),
            )
        )
    return quotes


def find_next_path(html: str) -> str | None:
    """ページネーションの「次へ」リンク path を返す。無ければ None。"""
    soup = BeautifulSoup(html, "html.parser")
    next_link = soup.select_one("li.next > a")
    if next_link is None:
        return None
    href = next_link.get("href")
    return href if isinstance(href, str) else None


def scrape_all(base_url: str = BASE_URL, start_path: str = START_PATH) -> list[Quote]:
    """全ページを巡回して引用文を収集する。"""
    if not is_allowed(base_url, start_path, USER_AGENT):
        raise PermissionError(f"robots.txt によりクロールが禁止されています: {base_url}{start_path}")

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    all_quotes: list[Quote] = []
    path: str | None = start_path
    page_no = 0
    while path:
        page_no += 1
        url = urljoin(base_url, path)
        resp = session.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()  # 4xx/5xx は例外で顕在化
        page_quotes = parse_quotes(resp.text)
        all_quotes.extend(page_quotes)
        print(f"[info] page {page_no}: {len(page_quotes)} 件取得 ({url})")
        path = find_next_path(resp.text)
        if path:
            time.sleep(POLITE_DELAY)
    return all_quotes


def save_csv(quotes: list[Quote], out_path: Path) -> None:
    """収集した引用文を CSV に保存する。"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["text", "author", "tags"])
        writer.writeheader()
        for q in quotes:
            writer.writerow(asdict(q))


def main() -> int:
    out_csv = Path(__file__).parent / "sample_output" / "quotes.csv"
    print(f"[start] {BASE_URL} のスクレイピングを開始します")
    quotes = scrape_all()
    if not quotes:
        # 空結果は成功と偽らない（honest fail-surface）
        print("[fail] 引用文が 1 件も取得できませんでした", file=sys.stderr)
        return 1
    save_csv(quotes, out_csv)
    print(f"[done] {len(quotes)} 件を {out_csv} に保存しました")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
