"""Canva Code 게시 링크에서 앱을 받아 갤러리 보관본을 만든다.

명세: docs/SPEC.md 3절(검증), 5-2절(처리 순서), 5-4절(세부 규칙), 9-1절(Windows 주의).

    # Forms 응답 CSV로 4팀 모두 보관
    python tools/archive_canva.py --csv tools/input/responses.csv

    # 링크 1개로 한 팀만 보관 (시험·재보관)
    python tools/archive_canva.py --url <게시 링크> --team team1

    # 저장소를 건드리지 않고 다른 폴더에 결과만 만들기
    python tools/archive_canva.py --url <게시 링크> --team team1 --out <폴더>
"""

import argparse
import base64
import csv
import datetime as dt
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.request import urlopen

# 학교망 보안 장비가 인증서를 바꿔 끼우므로 Windows 인증서 저장소로 확인한다 (9-1).
import truststore

truststore.inject_into_ssl()
import requests  # noqa: E402  (truststore 다음에 불러와야 한다)

ROOT = Path(__file__).resolve().parent.parent
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36 Edg/130.0"
)
TIMEOUT = 30
THUMB_SIZE = (820, 1180)
WAIT_ARCHIVE = 5    # 보관본 캡처 전 기다리는 시간(초): Tailwind 등 CDN을 받을 시간
WAIT_PUBLISHED = 12  # Canva 게시 페이지는 늦게 그려진다

REQUIRED_COLUMNS = [
    "팀 이름", "앱 이름", "한 줄 소개", "이 앱이 해결하는 불편",
    "꼭 필요한 기능 3개", "시험 문장", "앱 게시 링크", "공개 동의",
]
COL_TIMESTAMP = "타임스탬프"
COL_USER = "누가 쓰나요?"

SDK_NAMES = ("dataSdk", "elementSdk", "telemetrySdk", "frameEventsSdk")
EMBED_RE = re.compile(r"_assets/remote/embed/codelet/[A-Za-z0-9_-]+/index\.html")
CANVA_SCRIPT_RE = re.compile(
    r"""<script\b[^>]*\bsrc\s*=\s*["']/codelet/[^"']*["'][^>]*>\s*</script>[ \t]*\r?\n?""",
    re.IGNORECASE,
)
INLINE_SCRIPT_RE = re.compile(r"<script\b(?![^>]*\bsrc\s*=)[^>]*>(.*?)</script>", re.IGNORECASE | re.DOTALL)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
FEATURE_PREFIX_RE = re.compile(r"^\s*(?:\d+\s*[.)]|[-·•*])\s*")


class ArchiveError(Exception):
    """보관 실패 이유. 학생 앱 하나의 실패로 전체를 멈추지 않는다."""


class FatalError(Exception):
    """입력이 잘못되어 아무것도 바꾸지 않고 멈춰야 할 때."""


class Log:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.file = path.open("w", encoding="utf-8")

    def __call__(self, message: str = ""):
        print(message, flush=True)
        self.file.write(message + "\n")
        self.file.flush()

    def close(self):
        self.file.close()


# ---------- 받기 ----------

def make_session() -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    return session


def fetch(session: requests.Session, url: str, headers=None) -> requests.Response:
    last_error = None
    for _ in range(2):  # 실패하면 1번 더
        try:
            response = session.get(url, headers=headers or {}, timeout=TIMEOUT)
            response.raise_for_status()
            return response
        except requests.RequestException as error:
            last_error = error
    raise ArchiveError(f"받기 실패: {short_error(last_error)}")


def short_error(error: Exception) -> str:
    if isinstance(error, requests.HTTPError) and error.response is not None:
        return f"HTTP {error.response.status_code}"
    return type(error).__name__


def check_source_url(url: str) -> str:
    url = (url or "").strip()
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ArchiveError("https://로 시작하는 주소가 아님")
    host = parsed.hostname or ""
    if not (host == "canva.site" or host.endswith(".canva.site")):
        raise ArchiveError("Canva 게시 주소(*.canva.site)가 아님")
    return url


def download_app(session: requests.Session, source_url: str) -> str:
    """게시 페이지 → iframe 앱 주소 → 앱 HTML (3절 1~2)."""
    page = fetch(session, source_url).content.decode("utf-8", "replace")
    match = EMBED_RE.search(page)
    if not match:
        raise ArchiveError("게시 페이지에서 앱(codelet) 주소를 찾지 못함")

    parsed = urlparse(source_url)
    base_path = parsed.path if parsed.path.endswith("/") else parsed.path + "/"
    base = urlunparse((parsed.scheme, parsed.netloc, base_path, "", "", ""))
    embed_url = urljoin(base, match.group(0))

    response = fetch(session, embed_url, headers={"Referer": source_url, "Sec-Fetch-Dest": "iframe"})
    # 응답 헤더에 문자 인코딩이 없어 그냥 읽으면 한글이 깨진다 (9-1).
    app_html = response.content.decode("utf-8", "replace")
    if "<html" not in app_html.lower():
        raise ArchiveError("앱 HTML이 아닌 응답을 받음")
    return app_html


# ---------- 보관본 만들기 ----------

def html_comment_text(text: str) -> str:
    # HTML 주석 안에서는 "-->"·"<!--"만 막으면 된다. 한글 도메인(xn--…)의 "--"는 그대로 둔다.
    return text.replace("-->", "- ->").replace("<!--", "<! --")


def make_archive_html(original: str, source_url: str, archived_at: str) -> tuple[str, int]:
    archived, removed = CANVA_SCRIPT_RE.subn("", original)
    note = html_comment_text(
        f"보관본: 원본 {source_url} / 보관 {archived_at} / Canva 전용 스크립트 {removed}개 제거"
    )
    inject = ["<meta name=\"robots\" content=\"noindex\">", f"<!-- {note} -->"]
    if not re.search(r"<meta[^>]+charset", archived, re.IGNORECASE):
        inject.insert(0, "<meta charset=\"utf-8\">")
    block = "\n" + "\n".join(inject) + "\n"

    head = re.search(r"<head\b[^>]*>", archived, re.IGNORECASE)
    if head:
        archived = archived[:head.end()] + block + archived[head.end():]
    else:
        archived = block.lstrip("\n") + archived
    return archived, removed


def uses_canva_sdk(original: str) -> bool:
    body = "\n".join(INLINE_SCRIPT_RE.findall(original))
    return any(re.search(rf"\b{name}\b", body) for name in SDK_NAMES)


def page_title(app_html: str) -> str:
    match = TITLE_RE.search(app_html)
    return re.sub(r"\s+", " ", match.group(1)).strip() if match else ""


# ---------- 썸네일 ----------

def find_edge() -> str | None:
    candidates = [
        os.environ.get("EDGE_PATH", ""),
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Microsoft/Edge/Application/msedge.exe"),
        os.path.join(os.environ.get("ProgramFiles", ""), "Microsoft/Edge/Application/msedge.exe"),
    ]
    for path in candidates:
        if path and Path(path).is_file():
            return path
    return shutil.which("msedge")


class DevTools:
    """Edge 개발자 도구(CDP)에 붙는 최소 WebSocket 클라이언트. 추가 설치 없이 표준 라이브러리만 쓴다."""

    def __init__(self, ws_url: str):
        parsed = urlparse(ws_url)
        self.sock = socket.create_connection((parsed.hostname, parsed.port), timeout=60)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall(
            f"GET {parsed.path} HTTP/1.1\r\nHost: {parsed.netloc}\r\nUpgrade: websocket\r\n"
            f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n".encode()
        )
        reply = b""
        while b"\r\n\r\n" not in reply:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise OSError("DevTools 연결이 끊김")
            reply += chunk
        if b" 101 " not in reply.split(b"\r\n", 1)[0]:
            raise OSError("DevTools 연결 거부")
        self.buffer = reply.split(b"\r\n\r\n", 1)[1]
        self.next_id = 0

    def _read(self, n: int) -> bytes:
        while len(self.buffer) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise OSError("DevTools 연결이 끊김")
            self.buffer += chunk
        data, self.buffer = self.buffer[:n], self.buffer[n:]
        return data

    def _recv_message(self) -> str:
        parts = []
        while True:
            head = self._read(2)
            fin, opcode, length = head[0] & 0x80, head[0] & 0x0F, head[1] & 0x7F
            if length == 126:
                length = struct.unpack(">H", self._read(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", self._read(8))[0]
            payload = self._read(length)
            if opcode == 8:
                raise OSError("DevTools 연결이 닫힘")
            if opcode in (0, 1):
                parts.append(payload)
                if fin:
                    return b"".join(parts).decode("utf-8")

    def call(self, method: str, **params) -> dict:
        self.next_id += 1
        data = json.dumps({"id": self.next_id, "method": method, "params": params}).encode()
        mask = os.urandom(4)
        header = bytearray([0x81])
        if len(data) < 126:
            header.append(0x80 | len(data))
        elif len(data) < 65536:
            header += bytes([0x80 | 126]) + struct.pack(">H", len(data))
        else:
            header += bytes([0x80 | 127]) + struct.pack(">Q", len(data))
        self.sock.sendall(bytes(header) + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))
        while True:
            message = json.loads(self._recv_message())
            if message.get("id") == self.next_id:
                if "error" in message:
                    raise OSError(message["error"].get("message", "DevTools 오류"))
                return message.get("result", {})

    def close(self):
        self.sock.close()


def capture(target_url: str, out_png: Path, edge: str | None, wait_seconds: float) -> str | None:
    """Edge 헤드리스로 820×1180 캡처. 실패하면 이유를 돌려준다.

    Canva 게시 페이지는 늦게 그려져서 명령줄 --screenshot으로는 빈 화면이 찍힌다.
    그래서 개발자 도구로 붙어 실제로 기다린 뒤 찍고, 안 되면 명령줄 캡처로 대신한다.
    """
    if not edge:
        return "Edge를 찾지 못함"
    if out_png.exists():
        out_png.unlink()
    problem = capture_devtools(target_url, out_png, edge, wait_seconds)
    if problem is None:
        return None
    fallback = capture_cli(target_url, out_png, edge)
    return None if fallback is None else f"{problem}; {fallback}"


def capture_devtools(target_url: str, out_png: Path, edge: str, wait_seconds: float) -> str | None:
    profile = tempfile.mkdtemp(prefix="archive-edge-")
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    process = subprocess.Popen(
        [edge, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
         f"--remote-debugging-port={port}", f"--user-data-dir={profile}",
         f"--window-size={THUMB_SIZE[0]},{THUMB_SIZE[1]}", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    client = None
    try:
        page = None
        for _ in range(50):
            time.sleep(0.2)
            try:
                with urlopen(f"http://127.0.0.1:{port}/json", timeout=2) as response:
                    page = next((t for t in json.load(response) if t.get("type") == "page"), None)
                if page:
                    break
            except OSError:
                continue
        if not page:
            return "개발자 도구 연결 실패"
        client = DevTools(page["webSocketDebuggerUrl"])
        client.call("Emulation.setDeviceMetricsOverride", width=THUMB_SIZE[0], height=THUMB_SIZE[1],
                    deviceScaleFactor=1, mobile=False)
        client.call("Page.navigate", url=target_url)
        time.sleep(wait_seconds)
        shot = client.call("Page.captureScreenshot", format="png")
        out_png.write_bytes(base64.b64decode(shot["data"]))
        return None
    except (OSError, ValueError, KeyError) as error:
        return f"개발자 도구 캡처 실패({error})"
    finally:
        if client:
            client.close()
        process.kill()
        process.wait(timeout=10)
        shutil.rmtree(profile, ignore_errors=True)


def capture_cli(target_url: str, out_png: Path, edge: str) -> str | None:
    # 연달아 실행하면 결과가 갱신되지 않는 일이 있어 실행마다 새 프로필을 쓴다 (9-1).
    profile = tempfile.mkdtemp(prefix="archive-edge-")
    command = [
        edge, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
        f"--user-data-dir={profile}",
        f"--window-size={THUMB_SIZE[0]},{THUMB_SIZE[1]}",
        "--virtual-time-budget=8000",
        f"--screenshot={out_png.resolve().as_posix()}",  # 경로는 슬래시로 (9-1)
        target_url,
    ]
    try:
        subprocess.run(command, capture_output=True, timeout=90, check=False)
    except subprocess.TimeoutExpired:
        return "캡처 시간 초과"
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    if not out_png.is_file() or out_png.stat().st_size == 0:
        return "캡처 파일이 만들어지지 않음"
    return None


# ---------- CSV ----------

def read_csv(path: Path) -> list[dict]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            headers = [h.strip() for h in (reader.fieldnames or [])]
            missing = [c for c in REQUIRED_COLUMNS if c not in headers]
            if missing:
                raise FatalError("CSV에 필요한 열이 없습니다: " + ", ".join(missing))
            rows = []
            for index, row in enumerate(reader):
                clean = {(k or "").strip(): (v or "").strip() for k, v in row.items()}
                clean["_row"] = index + 2  # 머리글 다음 줄부터
                rows.append(clean)
            return rows
    except UnicodeDecodeError:
        raise FatalError("CSV를 UTF-8로 읽지 못했습니다. Google Sheets에서 CSV로 다시 내려받아 주세요.")


def parse_timestamp(text: str):
    """Google Sheets 한국어 형식(예: 2026. 11. 3 오후 3:04:05)과 ISO 형식을 읽는다."""
    m = re.search(
        r"(\d{4})\D+(\d{1,2})\D+(\d{1,2})\D*?(오전|오후|AM|PM)?\s*(\d{1,2}):(\d{2})(?::(\d{2}))?",
        text or "", re.IGNORECASE,
    )
    if not m:
        return None
    year, month, day, ampm, hour, minute, second = m.groups()
    hour = int(hour)
    if ampm in ("오후", "PM", "pm") and hour < 12:
        hour += 12
    if ampm in ("오전", "AM", "am") and hour == 12:
        hour = 0
    try:
        return dt.datetime(int(year), int(month), int(day), hour, int(minute), int(second or 0))
    except ValueError:
        return None


def pick_latest(rows: list[dict], log: Log) -> list[dict]:
    """팀마다 가장 늦게 낸 행만 남긴다 (5-4 중복 제출)."""
    by_team: dict[str, list[dict]] = {}
    for row in rows:
        by_team.setdefault(row["팀 이름"], []).append(row)

    chosen = []
    for team, team_rows in by_team.items():
        stamps = [parse_timestamp(r.get(COL_TIMESTAMP, "")) for r in team_rows]
        if len(team_rows) > 1 and all(stamps):
            ordered = [r for _, r in sorted(zip(stamps, team_rows), key=lambda p: (p[0], p[1]["_row"]))]
        else:
            ordered = sorted(team_rows, key=lambda r: r["_row"])
        latest = ordered[-1]
        for dropped in ordered[:-1]:
            log(f"  [중복] '{team}' {dropped['_row']}번 줄은 버리고 {latest['_row']}번 줄을 씁니다.")
        chosen.append(latest)
    return chosen


def split_features(text: str) -> list[str]:
    items = []
    for line in re.split(r"\r?\n", text or ""):
        line = FEATURE_PREFIX_RE.sub("", line).strip()
        if line:
            items.append(line)
    return items


# ---------- projects.json ----------

def load_projects(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise FatalError(f"projects.json을 읽지 못했습니다: {error}")


def save_projects(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


def team_label(project: dict) -> str:
    if project.get("teamName"):
        return project["teamName"].strip()
    number = re.sub(r"\D", "", project.get("id", ""))
    return f"{number}팀" if number else project.get("id", "")


# ---------- 팀 하나 처리 ----------

def backup_existing(team_dir: Path, backup_root: Path, stamp: str, log: Log):
    if team_dir.is_dir() and any(team_dir.iterdir()):
        target = backup_root / stamp / team_dir.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(team_dir), str(target))
        log(f"  기존 보관본을 {target.relative_to(backup_root.parent.parent).as_posix()}로 옮겼습니다.")


def archive_team(project: dict, source_url: str, fields: dict, ctx: dict) -> tuple[str, str]:
    """한 팀을 보관하고 (상태, 이유)를 돌려준다. project는 그 자리에서 고친다."""
    log: Log = ctx["log"]
    team_dir: Path = ctx["apps_dir"] / project["id"]
    today = ctx["today"]
    had_archive = (team_dir / "index.html").is_file()

    reason, valid_link = "", True
    try:
        url = check_source_url(source_url)
    except ArchiveError as error:
        original, reason, valid_link = None, str(error), False
    else:
        try:
            original = download_app(ctx["session"], url)
        except ArchiveError as error:
            original, reason = None, str(error)

    if original is None and had_archive and project.get("status") in ("archived", "archived-partial"):
        log(f"  [유지] 새로 받지 못해 이전 보관본을 그대로 둡니다: {reason}")
        return project["status"], f"이전 보관본 유지 ({reason})"

    backup_existing(team_dir, ctx["backup_root"], ctx["stamp"], log)
    team_dir.mkdir(parents=True, exist_ok=True)

    project.update({k: v for k, v in fields.items() if v not in (None, "", [])})
    project["sourceUrl"] = (source_url or "").strip()
    # Canva 게시 주소가 아니면 갤러리에서 그 주소로 보내지 않는다 (교사가 확인 뒤 직접 고침).
    project["sourceOpen"] = valid_link
    project["archivedAt"] = today

    if original is None:
        project["status"] = "link-only"
        project["usesCanvaData"] = False
        log(f"  [link-only] {reason}")
        if not valid_link:
            log("  Canva 게시 주소가 아니어서 [Canva 원본] 버튼을 막았습니다(sourceOpen: false).")
        elif ctx["thumbs"]:
            # 게시 페이지가 열릴 때만 캡처한다. 없는 페이지(404)를 썸네일로 쓰지 않는다.
            try:
                fetch(ctx["session"], project["sourceUrl"])
            except ArchiveError as error:
                log(f"  썸네일: 게시 페이지가 열리지 않아 만들지 않습니다({error}).")
            else:
                problem = capture(project["sourceUrl"], team_dir / "thumb.png", ctx["edge"], WAIT_PUBLISHED)
                log(f"  썸네일: {'게시 페이지 캡처' if not problem else '[경고] 실패 - ' + problem}")
        return "link-only", reason

    (team_dir / "original.html").write_text(original, encoding="utf-8", newline="")
    archived, removed = make_archive_html(original, project["sourceUrl"], today)
    (team_dir / "index.html").write_text(archived, encoding="utf-8", newline="")

    partial = uses_canva_sdk(original)
    project["usesCanvaData"] = partial
    project["status"] = "archived-partial" if partial else "archived"
    if not project.get("appName"):
        project["appName"] = page_title(original) or team_label(project)

    log(f"  앱 HTML {len(original.encode('utf-8')):,}바이트, Canva 스크립트 {removed}개 제거"
        + (", Canva 기능 사용 → archived-partial" if partial else ""))
    if removed == 0:
        log("  [경고] 지울 Canva 스크립트가 없었습니다. 원본 구조가 바뀌었는지 확인하세요.")

    if ctx["thumbs"]:
        problem = capture((team_dir / "index.html").resolve().as_uri(), team_dir / "thumb.png", ctx["edge"],
                          WAIT_ARCHIVE)
        log(f"  썸네일: {'보관본 캡처' if not problem else '[경고] 실패 - ' + problem}")
    return project["status"], "Canva 기능 사용" if partial else ""


# ---------- 실행 ----------

def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Canva Code 게시 링크로 갤러리 보관본을 만든다.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--csv", type=Path, help="Google Forms 응답 CSV")
    source.add_argument("--url", help="게시 링크 1개 (--team과 함께)")
    parser.add_argument("--team", help="--url로 보관할 팀 id (예: team1)")
    parser.add_argument("--out", type=Path, help="결과를 만들 다른 폴더 (저장소 파일은 바꾸지 않음)")
    parser.add_argument("--no-thumb", action="store_true", help="썸네일 캡처를 건너뜀")
    args = parser.parse_args(argv)
    if args.url and not args.team:
        parser.error("--url에는 --team이 필요합니다 (예: --team team1)")
    return args


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # 한글이 깨지지 않게 (9-1)
        except AttributeError:
            pass
    args = parse_args(argv)

    now = dt.datetime.now()
    stamp = now.strftime("%Y%m%d-%H%M%S")
    out_root = args.out.resolve() if args.out else ROOT
    log = Log(out_root / "tools" / "logs" / f"archive-{stamp}.log")
    log(f"보관 시작 {now:%Y-%m-%d %H:%M:%S} / 결과 폴더: {out_root.as_posix()}")

    try:
        # --out 폴더에 이미 결과가 있으면 그것을 이어서 고친다(같은 폴더에 여러 번 실행할 때).
        out_projects = out_root / "data" / "projects.json"
        data = load_projects(out_projects if out_projects.is_file() else ROOT / "data" / "projects.json")
        projects = {p["id"]: p for p in data.get("projects", [])}

        jobs = []  # (project, source_url, fields)
        if args.url:
            if args.team not in projects:
                raise FatalError(f"projects.json에 '{args.team}' 팀이 없습니다.")
            jobs.append((projects[args.team], args.url, {}))
        else:
            rows = read_csv(args.csv)
            log(f"CSV {len(rows)}줄을 읽었습니다.")
            by_label = {team_label(p): p for p in projects.values()}
            for row in pick_latest(rows, log):
                project = by_label.get(row["팀 이름"])
                if not project:
                    log(f"  [건너뜀] {row['_row']}번 줄: '{row['팀 이름']}' 팀이 projects.json에 없습니다.")
                    continue
                if not row["공개 동의"]:
                    log(f"  [건너뜀] {team_label(project)}: 공개 동의가 없습니다.")
                    continue
                features = split_features(row["꼭 필요한 기능 3개"])
                if len(features) != 3:
                    log(f"  [경고] {team_label(project)}: 기능이 {len(features)}개입니다(3개 기대).")
                jobs.append((project, row["앱 게시 링크"], {
                    "appName": row["앱 이름"],
                    "tagline": row["한 줄 소개"],
                    "problem": row["이 앱이 해결하는 불편"],
                    "user": row.get(COL_USER, ""),
                    "features": features,
                    "testSentence": row["시험 문장"],
                }))
    except FatalError as error:
        log(f"[멈춤] {error}")
        log.close()
        return 2

    ctx = {
        "log": log,
        "session": make_session(),
        "apps_dir": out_root / "apps",
        "backup_root": out_root / "tools" / "backup",
        "stamp": stamp,
        "today": now.strftime("%Y-%m-%d"),
        "edge": find_edge(),
        "thumbs": not args.no_thumb,
    }
    if ctx["thumbs"] and not ctx["edge"]:
        log("[경고] Microsoft Edge를 찾지 못해 썸네일을 만들지 않습니다.")

    results = []
    for project, source_url, fields in jobs:
        log(f"\n▶ {project['id']} ({team_label(project)}) {source_url}")
        try:
            status, reason = archive_team(project, source_url, fields, ctx)
        except Exception as error:  # 한 팀의 예상 못 한 오류로 전체를 멈추지 않는다
            status, reason = project.get("status", "?"), f"예상 못 한 오류: {error!r}"
            log(f"  [오류] {reason}")
        results.append((project["id"], team_label(project), status, reason))

    save_projects(out_root / "data" / "projects.json", data)

    log("\n결과")
    log("팀      | 이름           | 상태              | 이유")
    for team_id, label, status, reason in results:
        log(f"{team_id:<7} | {label:<14} | {status:<17} | {reason}")
    if not results:
        log("(보관한 팀이 없습니다)")
    log(f"\n로그: {log.path.as_posix()}")
    log.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
