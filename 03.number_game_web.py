import random

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="number-game-secret-key")


def render_page(message: str = "", tries: int = 0, finished: bool = False) -> str:
    if finished:
        result_box = f"""
        <p class="message success">&#127881; 정답입니다! 축하합니다! &#127881;</p>
        <p class="tries success">{tries}번 만에 맞추셨습니다!</p>
        """
        form = '<a class="button" href="/new">다시 시작하기</a>'
    else:
        result_box = f'<p class="message">{message}</p>' if message else ""
        result_box += f'<p class="tries">시도 횟수: {tries}</p>' if tries else ""
        form = """
        <form action="/guess" method="post">
            <input type="number" name="guess" min="1" max="100" placeholder="1~100" required autofocus>
            <button type="submit">제출</button>
        </form>
        """

    return f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>숫자 맞추기 게임</title>
        <style>
            body {{
                font-family: sans-serif;
                max-width: 400px;
                margin: 80px auto;
                text-align: center;
            }}
            input {{
                padding: 8px;
                font-size: 16px;
                width: 120px;
            }}
            button, .button {{
                padding: 8px 16px;
                font-size: 16px;
                margin-left: 8px;
                cursor: pointer;
                text-decoration: none;
                color: black;
                border: 1px solid #ccc;
                border-radius: 4px;
            }}
            .message {{
                font-size: 20px;
                font-weight: bold;
            }}
            .tries {{
                color: #555;
            }}
            .message.success {{
                font-size: 26px;
                color: #2e7d32;
            }}
            .tries.success {{
                font-size: 18px;
                font-weight: bold;
                color: #2e7d32;
            }}
        </style>
    </head>
    <body>
        <h1>1~100 숫자 맞추기</h1>
        {result_box}
        {form}
    </body>
    </html>
    """


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    if "answer" not in request.session:
        request.session["answer"] = random.randint(1, 100)
        request.session["tries"] = 0

    message = request.session.get("message", "")
    finished = request.session.get("finished", False)
    tries = request.session.get("tries", 0)
    return render_page(message=message, tries=tries, finished=finished)


@app.get("/new")
def new_game(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


@app.post("/guess")
def guess(request: Request, guess: str = Form("")):
    answer = request.session.get("answer")
    if answer is None:
        return RedirectResponse("/", status_code=303)

    try:
        guess_value = int(guess)
        if not (1 <= guess_value <= 100):
            raise ValueError
    except ValueError:
        request.session["message"] = "1~100 사이의 숫자를 입력해주세요."
        return RedirectResponse("/", status_code=303)

    request.session["tries"] = request.session.get("tries", 0) + 1
    tries = request.session["tries"]

    if guess_value < answer:
        request.session["message"] = "낮습니다."
    elif guess_value > answer:
        request.session["message"] = "높습니다."
    else:
        request.session["message"] = f"정답입니다! {tries}번만에 맞추셨습니다. 축하합니다!"
        request.session["finished"] = True

    return RedirectResponse("/", status_code=303)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
