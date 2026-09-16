import hashlib
import html
import json
import math
import os
import threading
from datetime import datetime

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="guestboard-secret-key")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "guestboard.json")
_lock = threading.Lock()

NAME_MAX_LENGTH = 20
MESSAGE_MAX_LENGTH = 500
PAGE_SIZE = 10

AVATAR_COLORS = ["#26A69A", "#00897B", "#4DB6AC", "#00796B", "#1DE9B6", "#0F9B8E"]


def load_entries() -> list:
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def save_entries(entries: list) -> None:
    tmp_path = DATA_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, DATA_FILE)


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def next_id(entries: list) -> int:
    return max((e["id"] for e in entries), default=0) + 1


def avatar_color(name: str) -> str:
    idx = sum(ord(c) for c in name) % len(AVATAR_COLORS)
    return AVATAR_COLORS[idx]


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def render_entry(entry: dict) -> str:
    name = html.escape(entry["name"])
    message = html.escape(entry["message"]).replace("\n", "<br>")
    created_at = html.escape(entry["created_at"])
    color = avatar_color(entry["name"])
    initial = html.escape(entry["name"][:1].upper()) if entry["name"] else "?"

    return f"""
    <div class="entry">
        <div class="entry-header">
            <div class="avatar" style="background:{color}">{initial}</div>
            <div class="entry-meta">
                <span class="entry-name">{name}</span>
                <span class="entry-date">{created_at}</span>
            </div>
        </div>
        <p class="entry-message">{message}</p>
        <form class="delete-form" action="/delete/{entry['id']}" method="post">
            <input type="password" name="password" placeholder="비밀번호" maxlength="50" required>
            <button type="submit">삭제</button>
        </form>
    </div>
    """


def render_pagination(page: int, total_pages: int) -> str:
    if total_pages <= 1:
        return ""

    links = []
    for p in range(1, total_pages + 1):
        css = "page-link current" if p == page else "page-link"
        links.append(f'<a class="{css}" href="/?page={p}">{p}</a>')

    return f'<div class="pagination">{"".join(links)}</div>'


def render_page(entries: list, total: int, page: int, total_pages: int, error: str = "") -> str:
    entries_html = "".join(render_entry(e) for e in entries) or (
        '<p class="empty">아직 남겨진 방명록이 없습니다. 첫 글을 남겨보세요!</p>'
    )
    error_html = f'<p class="error">{html.escape(error)}</p>' if error else ""
    pagination_html = render_pagination(page, total_pages)

    return f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>방명록</title>
        <style>
            * {{
                box-sizing: border-box;
            }}
            body {{
                font-family: "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
                background: linear-gradient(180deg, #E0F7F4 0%, #F5FDFC 200px);
                margin: 0;
                padding: 40px 16px 80px;
                color: #1F3D3A;
            }}
            .container {{
                max-width: 640px;
                margin: 0 auto;
            }}
            h1 {{
                text-align: center;
                font-size: 32px;
                margin-bottom: 4px;
                color: #0F766E;
            }}
            .subtitle {{
                text-align: center;
                color: #4C8A83;
                margin-top: 0;
                margin-bottom: 28px;
            }}
            .error {{
                background: #FFF1F0;
                color: #C0392B;
                border: 1px solid #F5C6C2;
                padding: 10px 14px;
                border-radius: 10px;
                margin-bottom: 16px;
                font-size: 14px;
            }}
            .write-form {{
                background: #FFFFFF;
                border-radius: 18px;
                padding: 20px;
                box-shadow: 0 8px 24px rgba(15, 118, 110, 0.10);
                margin-bottom: 32px;
            }}
            .write-form .row {{
                display: flex;
                gap: 10px;
                margin-bottom: 10px;
            }}
            .write-form input,
            .write-form textarea {{
                width: 100%;
                border: 1px solid #CDEDE8;
                background: #F7FEFC;
                border-radius: 10px;
                padding: 10px 12px;
                font-size: 14px;
                font-family: inherit;
                color: #1F3D3A;
            }}
            .write-form input:focus,
            .write-form textarea:focus {{
                outline: none;
                border-color: #2DD4BF;
                background: #FFFFFF;
            }}
            .write-form textarea {{
                min-height: 90px;
                resize: vertical;
                margin-bottom: 12px;
            }}
            .write-form button {{
                width: 100%;
                background: #14B8A6;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 12px;
                font-size: 15px;
                font-weight: bold;
                cursor: pointer;
                transition: background 0.15s ease;
            }}
            .write-form button:hover {{
                background: #0F9B8E;
            }}
            .entries-header {{
                display: flex;
                justify-content: space-between;
                color: #4C8A83;
                font-size: 14px;
                margin-bottom: 12px;
                padding: 0 4px;
            }}
            .entry {{
                background: #FFFFFF;
                border-radius: 16px;
                padding: 18px;
                margin-bottom: 14px;
                box-shadow: 0 4px 14px rgba(15, 118, 110, 0.08);
            }}
            .entry-header {{
                display: flex;
                align-items: center;
                gap: 10px;
                margin-bottom: 10px;
            }}
            .avatar {{
                width: 36px;
                height: 36px;
                border-radius: 50%;
                color: white;
                font-weight: bold;
                display: flex;
                align-items: center;
                justify-content: center;
                flex-shrink: 0;
            }}
            .entry-meta {{
                display: flex;
                flex-direction: column;
                line-height: 1.3;
            }}
            .entry-name {{
                font-weight: bold;
                color: #115E59;
            }}
            .entry-date {{
                font-size: 12px;
                color: #8AB6B0;
            }}
            .entry-message {{
                white-space: pre-wrap;
                word-break: break-word;
                margin: 0 0 12px 0;
                line-height: 1.6;
            }}
            .delete-form {{
                display: flex;
                justify-content: flex-end;
                gap: 6px;
            }}
            .delete-form input {{
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                padding: 5px 8px;
                font-size: 12px;
                width: 110px;
            }}
            .delete-form button {{
                border: none;
                background: #F0FBF9;
                color: #0F9B8E;
                border: 1px solid #CDEDE8;
                border-radius: 8px;
                padding: 5px 10px;
                font-size: 12px;
                cursor: pointer;
            }}
            .delete-form button:hover {{
                background: #E0F7F4;
            }}
            .empty {{
                text-align: center;
                color: #8AB6B0;
                padding: 40px 0;
            }}
            .pagination {{
                display: flex;
                justify-content: center;
                gap: 6px;
                margin-top: 20px;
                flex-wrap: wrap;
            }}
            .page-link {{
                text-decoration: none;
                color: #0F9B8E;
                border: 1px solid #CDEDE8;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 13px;
            }}
            .page-link.current {{
                background: #14B8A6;
                color: white;
                border-color: #14B8A6;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>&#128155; 방명록</h1>
            <p class="subtitle">따뜻한 한마디를 남겨주세요</p>

            {error_html}

            <form class="write-form" action="/write" method="post">
                <div class="row">
                    <input type="text" name="name" placeholder="이름" maxlength="{NAME_MAX_LENGTH}" required>
                    <input type="password" name="password" placeholder="비밀번호 (삭제 시 필요)" maxlength="50" required>
                </div>
                <textarea name="message" placeholder="방명록 내용을 남겨주세요" maxlength="{MESSAGE_MAX_LENGTH}" required></textarea>
                <button type="submit">남기기</button>
            </form>

            <div class="entries-header">
                <span>총 {total}개의 글</span>
                <span>{page} / {total_pages} 페이지</span>
            </div>

            <div class="entries">
                {entries_html}
            </div>

            {pagination_html}
        </div>
    </body>
    </html>
    """


@app.get("/", response_class=HTMLResponse)
def index(request: Request, page: int = 1):
    entries = load_entries()
    error = request.session.pop("error", "")

    total = len(entries)
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(1, min(page, total_pages))

    ordered = list(reversed(entries))
    start = (page - 1) * PAGE_SIZE
    page_entries = ordered[start:start + PAGE_SIZE]

    return render_page(page_entries, total=total, page=page, total_pages=total_pages, error=error)


@app.post("/write")
def write(request: Request, name: str = Form(""), password: str = Form(""), message: str = Form("")):
    name = name.strip()
    password = password.strip()
    message = message.strip()

    if not name or not password or not message:
        request.session["error"] = "이름, 비밀번호, 내용을 모두 입력해주세요."
        return RedirectResponse("/", status_code=303)

    with _lock:
        entries = load_entries()
        entry = {
            "id": next_id(entries),
            "name": name[:NAME_MAX_LENGTH],
            "password": hash_password(password),
            "message": message[:MESSAGE_MAX_LENGTH],
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "ip": get_client_ip(request),
        }
        entries.append(entry)
        save_entries(entries)

    return RedirectResponse("/", status_code=303)


@app.post("/delete/{entry_id}")
def delete(request: Request, entry_id: int, password: str = Form("")):
    with _lock:
        entries = load_entries()
        target = next((e for e in entries if e["id"] == entry_id), None)

        if target is None:
            return RedirectResponse("/", status_code=303)

        if target["password"] != hash_password(password):
            request.session["error"] = "비밀번호가 일치하지 않습니다."
            return RedirectResponse("/", status_code=303)

        entries = [e for e in entries if e["id"] != entry_id]
        save_entries(entries)

    return RedirectResponse("/", status_code=303)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
