# 小工具：取目前登入者（同步）
from fastapi import Request

def current_user(request: Request):
    return request.session.get("user")  # {id, username, role} 或 None

# === app.py ===
from typing import Optional
from pathlib import Path
import re 

from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware  
from db import get_conn
import psycopg 

# --- 初始化 ---
try:  # 雜湊函式載入
    from passlib.hash import bcrypt, pbkdf2_sha256
    HAS_BCRYPT = True
except Exception:
    HAS_BCRYPT = False

BASE_DIR = Path(__file__).resolve().parent  # 取得資料夾所在的實體路徑

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="change-me")  # 讓 request.session 可用，secret_key 用來加密/簽章 session cookie
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))  # 指定模板資料夾 之後回傳(reutrn)頁面會用
app.mount("/www", StaticFiles(directory=str(BASE_DIR / "www")), name="www")  # 靜態檔案掛載

# --------------------------------
# 首頁：專案列表
# --------------------------------
@app.get("/", response_class=HTMLResponse)  # 宣告首頁路由
def projects_list(request: Request):
    user = current_user(request)  # 讀 session 取得目前登入者
    tab = request.query_params.get("tab", "open")  # 讀網址列參數，預設是 "open"
    stats = {"open": 0, "progress": 0, "closed": 0}  # 統計數字
    projects = []  # 先給空清單，等下依角色查 DB 填資料

    with get_conn() as conn, conn.cursor() as cur:  # 開 DB 連線

        # 未登入（訪客）：僅顯示投放中
        if not user:
            cur.execute(""" 
                SELECT p.id, p.title, p.status, p.created_at,
                       LEFT(p.description, 200) AS description
                FROM projects p
                WHERE p.status='open'
                ORDER BY p.id DESC
            """)
            projects = [
                {"id": a, "title": b, "status": c, "created_at": d, "description": e}
                for (a, b, c, d, e) in cur.fetchall()  # 取出所有列
            ]

        # 委託人
        elif user["role"] == "client":
            # 數量統計
            for k, cond in {
                "open": "status='open'",
                "progress": "status IN ('in_progress','reopened')",
                "closed": "status='closed'",
            }.items():
                cur.execute(
                    f"SELECT COUNT(*) FROM projects WHERE client_id=%s AND {cond}",
                    (user["id"],),
                )
                stats[k] = cur.fetchone()[0]

            # 清單
            if tab == "open":  # 投放中
                cur.execute("""
                    SELECT p.id, p.title, p.status, p.created_at,
                           LEFT(p.description, 200) AS description,
                           (SELECT COUNT(*) FROM bids b WHERE b.project_id=p.id) AS bid_count
                    FROM projects p
                    WHERE p.client_id=%s AND p.status='open'
                    ORDER BY p.id DESC
                """, (user["id"],))
                projects = [
                    {"id": a, "title": b, "status": c, "created_at": d,
                     "description": e, "bid_count": f}
                    for (a, b, c, d, e, f) in cur.fetchall()
                ]

            elif tab == "progress":  # 進行中
                cur.execute("""
                    SELECT p.id, p.title, p.status, p.created_at,
                           LEFT(p.description, 200) AS description,
                           (SELECT COUNT(*) FROM deliveries d WHERE d.project_id=p.id) AS delivery_count
                    FROM projects p
                    WHERE p.client_id=%s AND p.status IN ('in_progress','reopened')
                    ORDER BY p.id DESC
                """, (user["id"],))
                projects = [
                    {"id": a, "title": b, "status": c, "created_at": d,
                     "description": e, "delivery_count": f}
                    for (a, b, c, d, e, f) in cur.fetchall()
                ]

            else:  # 已結案
                cur.execute("""
                    SELECT p.id, p.title, p.status, p.created_at,
                           LEFT(p.description, 200) AS description
                    FROM projects p
                    WHERE p.client_id=%s AND p.status='closed'
                    ORDER BY p.id DESC
                """, (user["id"],))
                projects = [
                    {"id": a, "title": b, "status": c, "created_at": d, "description": e}
                    for (a, b, c, d, e) in cur.fetchall()
                ]

        # 接案人
        elif user["role"] == "freelancer":
            # 數量統計
            cur.execute("SELECT COUNT(*) FROM projects WHERE status='open'")
            stats["open"] = cur.fetchone()[0]

            cur.execute("""
                SELECT COUNT(*) FROM projects p
                JOIN bids b ON b.id = p.awarded_bid_id
                WHERE b.freelancer_id=%s AND p.status IN ('in_progress','reopened')
            """, (user["id"],))
            stats["progress"] = cur.fetchone()[0]

            cur.execute("""
                SELECT COUNT(*) FROM projects p
                JOIN bids b ON b.id = p.awarded_bid_id
                WHERE b.freelancer_id=%s AND p.status='closed'
            """, (user["id"],))
            stats["closed"] = cur.fetchone()[0]

            # 清單
            if tab == "open":
                cur.execute("""
                    SELECT p.id, p.title, p.status, p.created_at,
                           LEFT(p.description, 200) AS description,
                           (SELECT COUNT(*) FROM bids b
                            WHERE b.project_id=p.id AND b.freelancer_id=%s) AS has_bid
                    FROM projects p
                    WHERE p.status='open'
                    ORDER BY p.id DESC
                """, (user["id"],))
                projects = [
                    {"id": a, "title": b, "status": c, "created_at": d,
                     "description": e, "has_bid": (f > 0)}
                    for (a, b, c, d, e, f) in cur.fetchall()
                ]

            elif tab == "progress":
                cur.execute("""
                    SELECT p.id, p.title, p.status, p.created_at,
                           LEFT(p.description, 200) AS description,
                           (SELECT COUNT(*) FROM deliveries d
                            WHERE d.project_id=p.id AND d.freelancer_id=%s) AS my_delivery_count
                    FROM projects p
                    JOIN bids b ON b.id = p.awarded_bid_id
                    WHERE b.freelancer_id=%s AND p.status IN ('in_progress','reopened')
                    ORDER BY p.id DESC
                """, (user["id"], user["id"]))
                projects = [
                    {"id": a, "title": b, "status": c, "created_at": d,
                     "description": e, "my_delivery_count": f}
                    for (a, b, c, d, e, f) in cur.fetchall()
                ]

            else:  # closed
                cur.execute("""
                    SELECT p.id, p.title, p.status, p.created_at,
                           LEFT(p.description, 200) AS description
                    FROM projects p
                    JOIN bids b ON b.id = p.awarded_bid_id
                    WHERE b.freelancer_id=%s AND p.status='closed'
                    ORDER BY p.id DESC
                """, (user["id"],))
                projects = [
                    {"id": a, "title": b, "status": c, "created_at": d, "description": e}
                    for (a, b, c, d, e) in cur.fetchall()
                ]

    return templates.TemplateResponse(
        "projects_list.html",
        {"request": request, "user": user, "tab": tab, "projects": projects, "stats": stats},
    )


# ----------------
# 新增專案
# ----------------
@app.get("/projects/create")
def project_create_page(request: Request):
    user = current_user(request)
    if not user or user["role"] != "client":
        return RedirectResponse("/", 302)
    return templates.TemplateResponse("project_create.html", {"request": request})


@app.post("/projects/create")
def project_create(request: Request,
                   title: str = Form(...),
                   description: str = Form(...),
                   budget: Optional[int] = Form(None)):
    user = current_user(request)
    # 後端再次保護
    if not user:
        return RedirectResponse("/login", 302)
    if user["role"] != "client":
        return RedirectResponse("/", 302)

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            INSERT INTO projects (title, description, client_id, budget)
            VALUES (%s, %s, %s, %s)
        """, (title, description, user["id"], budget))
        conn.commit()  # 確保有被寫入
    return RedirectResponse("/", 302)


# ----------------
# 案子詳細資料
# ----------------
from psycopg.rows import dict_row

@app.get("/projects/{id}")
def project_detail(request: Request, id: int):
    user = current_user(request) 

    # 讀專案（用 dict_row，欄位有名稱，不用數字 index）
    with get_conn() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT
                p.id,
                p.title,
                p.description,
                p.status,
                p.created_at,
                p.budget,                         
                u.username      AS client_name,
                u.id            AS client_id,
                p.awarded_bid_id,  -- 目前得標的
                (SELECT b.freelancer_id
                   FROM bids b
                  WHERE b.id = p.awarded_bid_id) AS awarded_freelancer_id
            FROM projects p
            JOIN users u ON p.client_id = u.id
            WHERE p.id = %s
        """, (id,))
        row = cur.fetchone()
        if not row:
            return RedirectResponse("/", 302)

        # 正規化狀態（避免 CHAR 尾巴空白 / 大小寫）
        status = (row["status"] or "").strip().lower()

        project = {
            "id": row["id"],
            "title": row["title"],
            "description": row["description"],
            "status": status,
            "created_at": row["created_at"],
            "budget": row["budget"],
            "client_name": row["client_name"],
            "client_id": row["client_id"],
            "awarded_bid_id": row["awarded_bid_id"],
            "awarded_freelancer_id": row["awarded_freelancer_id"],
        }

    # 讀報價（依角色）
    bids = []
    with get_conn() as conn, conn.cursor(row_factory=dict_row) as cur:
        if user and user["role"] == "client" and user["id"] == project["client_id"]: # 案主可以看到所有人的報價
            cur.execute("""
                SELECT b.id, b.price, b.message, b.created_at, fu.username AS freelancer
                FROM bids b
                JOIN users fu ON fu.id = b.freelancer_id
                WHERE b.project_id = %s
                ORDER BY b.price ASC, b.created_at ASC
            """, (id,))
            bids = cur.fetchall()
        elif user and user["role"] == "freelancer":
            cur.execute("""
                SELECT id, price, message, created_at
                FROM bids
                WHERE project_id=%s AND freelancer_id=%s
            """, (id, user["id"]))
            r = cur.fetchone()
            if r:
                bids = [{
                    "id": r["id"],
                    "price": r["price"],
                    "message": r["message"],
                    "created_at": r["created_at"],
                    "freelancer": user["username"],
                }]

    # 讀結案檔案
    with get_conn() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT d.filename, d.note, d.created_at, u.username AS freelancer
            FROM deliveries d
            JOIN users u ON u.id = d.freelancer_id
            WHERE d.project_id = %s
            ORDER BY d.created_at DESC
        """, (id,))
        deliveries = cur.fetchall()

    return templates.TemplateResponse(
        "project_detail.html",
        {"request": request, "project": project, "user": user, "bids": bids, "deliveries": deliveries}
    )


# ----------------
# 顯示編輯表單 / 接收編輯送出
# ----------------
@app.get("/projects/{project_id}/edit")
def edit_project_page(request: Request, project_id: int):
    user = current_user(request)
    if not user:
        return RedirectResponse("/login", 302)

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, title, description, status, client_id FROM projects WHERE id=%s", (project_id,))
        row = cur.fetchone()
        if not row:
            return RedirectResponse("/", 302)
        pid, title, desc, status, client_id = row

        # 已有報價不能編輯
        cur.execute("SELECT EXISTS (SELECT 1 FROM bids WHERE project_id=%s)", (project_id,))
        has_bids = cur.fetchone()[0]

        if user["id"] != client_id or status != "open":
            return RedirectResponse(f"/projects/{project_id}", 302)

    return templates.TemplateResponse("project_edit.html", {
        "request": request,
        "project": {"id": pid, "title": title, "description": desc}
    })


@app.post("/projects/{project_id}/edit")
def edit_project_submit(request: Request, project_id: int,
                        title: str = Form(...), description: str = Form(...)):
    user = current_user(request)
    if not user:
        return RedirectResponse("/login", 302)

    with get_conn() as conn, conn.cursor() as cur:
        # 僅限本人且 open 狀態才可編輯
        cur.execute("SELECT client_id, status FROM projects WHERE id=%s", (project_id,))
        row = cur.fetchone()
        if not row or row[0] != user["id"] or row[1] != "open":
            return RedirectResponse(f"/projects/{project_id}", 302)
        
        # 有報價就不能編輯
        cur.execute("SELECT EXISTS (SELECT 1 FROM bids WHERE project_id=%s)", (project_id,))
        has_bids = cur.fetchone()[0]
        if has_bids:
            return RedirectResponse(f"/projects/{project_id}?e=edit_locked", 302)

        cur.execute("""
            UPDATE projects SET title=%s, description=%s WHERE id=%s
        """, (title, description, project_id))
        conn.commit()

    return RedirectResponse(f"/projects/{project_id}", 302)


# ----------------
    # 刪除案子
# ----------------
@app.post("/projects/{project_id}/delete")
def delete_project(request: Request, project_id: int):
    user = current_user(request)
    if not user:
        return RedirectResponse("/login", 302)

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT client_id, status FROM projects WHERE id=%s", (project_id,))
        row = cur.fetchone()
        if not row or row[0] != user["id"] or row[1] != "open":
            return RedirectResponse(f"/projects/{project_id}", 302)
        
        # 已有報價就不能刪除
        cur.execute("SELECT EXISTS (SELECT 1 FROM bids WHERE project_id=%s)", (project_id,))
        has_bids = cur.fetchone()[0]
        if has_bids:
            return RedirectResponse(f"/projects/{project_id}?e=delete_locked", 302)

        cur.execute("DELETE FROM projects WHERE id=%s", (project_id,))
        conn.commit()

    return RedirectResponse("/", 302)


# ----------------
# 接受報價（選標）
# ----------------
@app.post("/projects/{project_id}/award/{bid_id}")
def award_bid(request: Request, project_id: int, bid_id: int):
    user = current_user(request)
    if not user:
        return RedirectResponse("/login", 302)

    with get_conn() as conn, conn.cursor() as cur:
        # 取得專案確認是本人委託
        cur.execute("SELECT client_id FROM projects WHERE id=%s", (project_id,))
        row = cur.fetchone()
        if not row or row[0] != user["id"]:
            return RedirectResponse(f"/projects/{project_id}", 302)

        # 更新狀態與中標報價
        cur.execute("""
            UPDATE projects
            SET awarded_bid_id=%s, status='in_progress'
            WHERE id=%s
        """, (bid_id, project_id))
        conn.commit()

    return RedirectResponse(f"/projects/{project_id}", 302)


# ----------------
# 上傳結案檔案
# ----------------

UPLOAD_DIR = BASE_DIR / "www" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@app.post("/deliveries/{project_id}")
async def upload_delivery(
    request: Request,
    project_id: int,
    file: UploadFile = File(...),
    note: str = Form("")
):
    user = current_user(request)
    if not user:
        return RedirectResponse("/login", 302)
    if user["role"] != "freelancer":
        return RedirectResponse(f"/projects/{project_id}", 302)

    # 先查專案狀態與中標者
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT p.status AS proj_status, b.freelancer_id AS awarded_freelancer_id
            FROM projects p
            JOIN bids b ON b.id = p.awarded_bid_id
            WHERE p.id = %s
        """, (project_id,))
        row = cur.fetchone()
        if not row:
            return RedirectResponse(f"/projects/{project_id}", 302)

        proj_status, awarded_freelancer_id = row

        # 僅限中標者，且狀態必須允許上傳
        if awarded_freelancer_id != user["id"] or proj_status not in ('in_progress', 'reopened'):
            return RedirectResponse(f"/projects/{project_id}", 302)

        # 檢查是否已上傳過（同一專案、同一人）
        cur.execute("""
            SELECT id, filename
            FROM deliveries
            WHERE project_id=%s AND freelancer_id=%s
        """, (project_id, user["id"]))
        prev = cur.fetchall()

        if prev:
            # 非退件狀態：拒絕重複上傳
            if proj_status != 'reopened':
                return RedirectResponse(f"/projects/{project_id}?filedup=1", 302)
            # 退件狀態：清理舊檔與紀錄後才允許上傳
            for _id, fname in prev:
                p = UPLOAD_DIR / fname
                if p.exists():
                    p.unlink()
            cur.execute("""
                DELETE FROM deliveries
                WHERE project_id=%s AND freelancer_id=%s
            """, (project_id, user["id"]))
            conn.commit()

    # 儲存新檔
    dest = UPLOAD_DIR / file.filename
    with open(dest, "wb") as f:
        f.write(await file.read())

    # 寫入DB
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            INSERT INTO deliveries (project_id, freelancer_id, filename, note)
            VALUES (%s,%s,%s,%s)
        """, (project_id, user["id"], file.filename, note))
        conn.commit()

    # 若是退件狀態，上傳後自動改回進行中
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            UPDATE projects
            SET status='in_progress'
            WHERE id=%s AND status='reopened'
        """, (project_id,))
        conn.commit()

    return RedirectResponse(f"/projects/{project_id}", 302)


# ----------------
# 關閉案子 / 退件
# ----------------
# 關專案
@app.post("/projects/{project_id}/close")
def close_project(request: Request, project_id: int):
    user = current_user(request)
    if not user:
        return RedirectResponse("/login", 302)

    with get_conn() as conn, conn.cursor() as cur:
        # 確認專案是該使用者委託的
        cur.execute("SELECT client_id, status FROM projects WHERE id=%s", (project_id,))
        row = cur.fetchone()
        if not row or row[0] != user["id"] or row[1] != "in_progress":
            return RedirectResponse(f"/projects/{project_id}", 302)

        # 更新狀態為 closed
        cur.execute("""
            UPDATE projects
            SET status='closed'
            WHERE id=%s
        """, (project_id,))
        conn.commit()

    return RedirectResponse(f"/projects/{project_id}", 302)

# 退件
@app.post("/projects/{project_id}/reject")
def reject_project(request: Request, project_id: int):
    user = current_user(request)
    if not user:
        return RedirectResponse("/login", 302)

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT client_id, status FROM projects WHERE id=%s", (project_id,))
        row = cur.fetchone()
        if not row or row[0] != user["id"] or row[1] != "in_progress":
            return RedirectResponse(f"/projects/{project_id}", 302)

        # 改成退件狀態(刪掉檔案 且 接案人可以在船檔案)
        cur.execute("""
            SELECT b.freelancer_id, d.filename
            FROM projects p
            JOIN bids b ON b.id = p.awarded_bid_id
            LEFT JOIN deliveries d ON d.project_id = p.id AND d.freelancer_id = b.freelancer_id
            WHERE p.id=%s
        """, (project_id,))
        rows = cur.fetchall()
        for fid, fname in rows:
            if fname:
                file_path = UPLOAD_DIR / fname
                if file_path.exists():
                    file_path.unlink()
        cur.execute("DELETE FROM deliveries WHERE project_id=%s", (project_id,))
        conn.commit()

        # 更新狀態為退件
        cur.execute("UPDATE projects SET status='reopened' WHERE id=%s", (project_id,))
        conn.commit()

    return RedirectResponse(f"/projects/{project_id}", 302)


# ----------------
# 送出報價
# ----------------
@app.post("/bids/{project_id}")
def create_bid(request: Request, project_id: int,
               price: int = Form(...),
               message: str = Form("")):
    user = current_user(request)
    if not user:
        return RedirectResponse("/login", 302)
    if user["role"] != "freelancer":
        return RedirectResponse(f"/projects/{project_id}", 302)

    with get_conn() as conn, conn.cursor() as cur:
        # 防止重複報價（也可交給 UNIQUE，但這樣訊息更友善）
        cur.execute("SELECT 1 FROM bids WHERE project_id=%s AND freelancer_id=%s",
                    (project_id, user["id"]))
        if cur.fetchone():  # 關閉連線防重檢查
            return RedirectResponse(f"/projects/{project_id}?dup=1", 302)  # 倒回擬以投標

        cur.execute("""
            INSERT INTO bids (project_id, freelancer_id, price, message)
            VALUES (%s,%s,%s,%s)
        """, (project_id, user["id"], price, message))
        conn.commit()

    return RedirectResponse(f"/projects/{project_id}", 302)


# ----------------
# 登入 / 登出 / 註冊
# ----------------
@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, username, password_hash, role FROM users WHERE username=%s", (username,))
        row = cur.fetchone()
    if not row:
        return RedirectResponse("/login?e=1", 302)  # 帶錯誤訊息

    uid, uname, pw_hash, role = row
    ok = False

    # 明文（相容舊資料）
    if pw_hash.startswith("plain:"):
        ok = (pw_hash[6:] == password)
        # 首登自動轉 bcrypt
        if ok and HAS_BCRYPT:
            try:
                new_hash = bcrypt.hash(password)
                with get_conn() as conn, conn.cursor() as cur:
                    cur.execute("UPDATE users SET password_hash=%s WHERE id=%s", (new_hash, uid))
                    conn.commit()
            except Exception:
                pass
    else:
        # 2) bcrypt
        if HAS_BCRYPT and (pw_hash.startswith("$2a$") or pw_hash.startswith("$2b$") or pw_hash.startswith("$2y$")):
            try:
                ok = bcrypt.verify(password, pw_hash)
            except Exception:
                ok = False

        # 3) pbkdf2_sha256
        if not ok and pw_hash.startswith("$pbkdf2-sha256$"):
            try:
                ok = pbkdf2_sha256.verify(password, pw_hash)
            except Exception:
                ok = False

    if not ok:
        return RedirectResponse("/login?e=1", 302)

    request.session["user"] = {"id": uid, "username": uname, "role": role}
    return RedirectResponse("/", 302)


# 登出
@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", 302)

# 註冊
@app.get("/register")
def register_page(request: Request):
    e = request.query_params.get("e")   # 取得 ?e=... 錯誤代碼
    return templates.TemplateResponse("register.html", {"request": request, "e": e})

@app.post("/register")
def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    password2: str = Form(...),
    role: str = Form(...),
    full_name: str = Form(...),
    phone: str = Form(""),
    email: str = Form(""),   
    agree: str = Form(None),
):
    # ---------- 驗證 ----------
    if role not in ("client", "freelancer"):
        return RedirectResponse("/register?e=role", status_code=302)
    if password != password2:
        return RedirectResponse("/register?e=pwd", status_code=302)
    if not agree:
        return RedirectResponse("/register?e=agree", status_code=302)
    if not full_name.strip():
        return RedirectResponse("/register?e=fullname", status_code=302)
    #if phone and not re.match(r"^[0-9+\-() ]{8,20}$", phone):
    #    return RedirectResponse("/register?e=phone", status_code=302)
    #if not email.strip():
    #    return RedirectResponse("/register?e=email", status_code=302)

    # ---------- 檢查使用者名稱重複 ----------
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT 1 FROM users WHERE username=%s;", (username,))
        if cur.fetchone():
            return RedirectResponse("/register?e=user", status_code=302)

        try:
            # 雜湊密碼
            try:
                if HAS_BCRYPT:
                    hashed = bcrypt.hash(password)
                else:
                    from passlib.hash import pbkdf2_sha256 as pbk
                    hashed = pbk.hash(password)
            except Exception:
                hashed = f"plain:{password}"

            # 送進 DB
            print("[DEBUG] about to insert:", username, role, full_name, phone, email)
            cur.execute("""
                INSERT INTO users (username, password_hash, role, full_name, phone, email)
                VALUES (%s,%s,%s,%s,%s,%s);
            """, (username, hashed, role, full_name, (phone or None), (email or None)))
            print("[DEBUG] rowcount after insert:", cur.rowcount)

            conn.commit()
            print("[DEBUG] committed insert for:", username)

        except Exception as e:
            import traceback
            traceback.print_exc()
            # 讓你在網址就能看到錯誤摘要（同時 console 會印完整堆疊）
            msg = str(e).replace(" ", "_")[:120]
            return RedirectResponse(f"/register?e=dberr:{msg}", status_code=302)

    return RedirectResponse("/register?ok=1", status_code=302)
