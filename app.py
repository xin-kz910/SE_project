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
import os
import uuid

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
                SELECT p.id, p.title, p.status, p.created_at, p.deadline,
                    LEFT(p.description, 200) AS description
                FROM projects p
                WHERE p.status='open'
                ORDER BY p.id DESC
            """)
            projects = [
                {
                    "id": a,
                    "title": b,
                    "status": c,
                    "created_at": d,
                    "deadline": e,
                    "description": f
                }
                for (a, b, c, d, e, f) in cur.fetchall()
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
                    SELECT p.id, p.title, p.status, p.created_at, p.deadline,
                           LEFT(p.description, 200) AS description,
                           (SELECT COUNT(*) FROM bids b WHERE b.project_id=p.id) AS bid_count
                    FROM projects p
                    WHERE p.client_id=%s AND p.status='open'
                    ORDER BY p.id DESC
                """, (user["id"],))
                projects = [
                    {
                        "id": a,
                        "title": b,
                        "status": c,
                        "created_at": d,
                        "deadline": e,
                        "description": f,
                        "bid_count": g
                    }
                    for (a, b, c, d, e, f, g) in cur.fetchall()
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
                    SELECT p.id, p.title, p.status, p.created_at, p.deadline,
                           LEFT(p.description, 200) AS description,
                           (SELECT COUNT(*) FROM bids b
                            WHERE b.project_id=p.id AND b.freelancer_id=%s) AS has_bid
                    FROM projects p
                    WHERE p.status='open'
                    ORDER BY p.id DESC
                """, (user["id"],))
                projects = [
                    {
                        "id": a,
                        "title": b,
                        "status": c,
                        "created_at": d,
                        "deadline": e,
                        "description": f,
                        "has_bid": (g > 0)
                    }
                    for (a, b, c, d, e, f, g) in cur.fetchall()
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
        {"request": request, "user": user, "tab": tab, "projects": projects, "stats": stats,"now": datetime.now()}
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


from datetime import datetime

@app.post("/projects/create")
def project_create(request: Request,
                   title: str = Form(...),
                   description: str = Form(...),
                   budget: Optional[int] = Form(None),
                   deadline: str = Form(None)):  # ⭐ 新增 deadline
    user = current_user(request)
    
    # 再次保護：未登入或不是 client 無法建立專案
    if not user:
        return RedirectResponse("/login", 302)
    if user["role"] != "client":
        return RedirectResponse("/", 302)

    # ⭐ 轉換 deadline 字串（datetime-local → datetime）
    dl_value = None
    if deadline:
        try:
            dl_value = datetime.fromisoformat(deadline)
        except Exception:
            dl_value = None   # 轉換錯誤時避免炸掉

    # ⭐ 寫入資料庫（包含 deadline）
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            INSERT INTO projects (title, description, client_id, budget, deadline)
            VALUES (%s, %s, %s, %s, %s)
        """, (title, description, user["id"], budget, dl_value))
        conn.commit()

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
                p.deadline, 
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
            "deadline": row["deadline"],
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
                SELECT b.id, b.price, b.message, b.created_at, b.proposal_filename, b.proposal_original_name, fu.username AS freelancer
                FROM bids b
                JOIN users fu ON fu.id = b.freelancer_id
                WHERE b.project_id = %s
                ORDER BY b.price ASC, b.created_at ASC
            """, (id,))
            bids = cur.fetchall()
        elif user and user["role"] == "freelancer":
            cur.execute("""
                SELECT id, price, message, created_at, proposal_filename, proposal_original_name
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
            ORDER BY d.created_at ASC
        """, (id,))
        deliveries = cur.fetchall()

    return templates.TemplateResponse(
        "project_detail.html",
        {"request": request, "project": project, "user": user, "bids": bids, "deliveries": deliveries, "now": datetime.now()}
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
                        title: str = Form(...), 
                        description: str = Form(...),
                        deadline: str = Form(None)):      # ⭐ 新增 deadline 欄位
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

        # ⭐ 轉換 deadline → datetime（若為空則保留 None）
        dl_value = None
        if deadline:
            try:
                dl_value = datetime.fromisoformat(deadline)
            except:
                dl_value = None

        # ⭐ 更新含 deadline
        cur.execute("""
            UPDATE projects
            SET title=%s, description=%s, deadline=%s
            WHERE id=%s
        """, (title, description, dl_value, project_id))

        conn.commit()

    return RedirectResponse(f"/projects/{project_id}", 302)

from datetime import datetime, timedelta

@app.post("/projects/{project_id}/reopen_bids")
def reopen_bids(request: Request, project_id: int):
    user = current_user(request)

    # 必須登入
    if not user:
        return RedirectResponse("/login", 302)

    with get_conn() as conn, conn.cursor() as cur:

        # 檢查該專案是否屬於此委託人
        cur.execute("SELECT client_id, deadline FROM projects WHERE id=%s", (project_id,))
        row = cur.fetchone()
        if not row:
            return RedirectResponse("/", 302)

        client_id, old_deadline = row

        if client_id != user["id"]:
            return RedirectResponse(f"/projects/{project_id}", 302)

        # ⭐ 重新設定 deadline（往後延 7 天）
        new_deadline = datetime.now() + timedelta(days=7)

        cur.execute("""
            UPDATE projects 
            SET deadline=%s
            WHERE id=%s
        """, (new_deadline, project_id))

        conn.commit()

    # Done，回到專案頁面
    return RedirectResponse(f"/projects/{project_id}?reopened=1", 302)




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
# 接受報價（完整規格）
# ----------------
@app.post("/projects/{project_id}/award/{bid_id}")
def award_bid(request: Request, project_id: int, bid_id: int):
    user = current_user(request)
    if not user:
        return RedirectResponse("/login", 302)

    from datetime import datetime

    with get_conn() as conn, conn.cursor(row_factory=dict_row) as cur:

        # 1️⃣ 取得專案資訊：確認委託人 + deadline + 是否已選標
        cur.execute("""
            SELECT client_id, awarded_bid_id, deadline
            FROM projects
            WHERE id=%s
        """, (project_id,))
        project = cur.fetchone()

        if not project:
            return RedirectResponse("/", 302)

        # 不是委託人 -> 禁止
        if project["client_id"] != user["id"]:
            return RedirectResponse(f"/projects/{project_id}", 302)

        # 已選過人 -> 禁止重選
        if project["awarded_bid_id"]:
            return RedirectResponse(f"/projects/{project_id}?already_awarded=1", 303)

        # 截止前不得選人
        if project["deadline"] and datetime.now() < project["deadline"]:
            return RedirectResponse(f"/projects/{project_id}?too_early=1", 303)

        # 2️⃣ 確認 bid 是否真的屬於此 project
        cur.execute("""
            SELECT freelancer_id
            FROM bids
            WHERE id=%s AND project_id=%s
        """, (bid_id, project_id))
        bid = cur.fetchone()

        if not bid:
            return RedirectResponse(f"/projects/{project_id}?invalid_bid=1", 303)

        # 3️⃣ 寫入得標者 + 改狀態為進行中
        cur.execute("""
            UPDATE projects
            SET awarded_bid_id=%s, status='in_progress'
            WHERE id=%s
        """, (bid_id, project_id))
        conn.commit()

    # 成功訊息（前端可 popup）
    return RedirectResponse(f"/projects/{project_id}?awarded=1", 303)

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

    # 僅接案者
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

        # 僅限中標者，上傳必須在 in_progress 或 reopened
        if awarded_freelancer_id != user["id"] or proj_status not in ('in_progress', 'reopened'):
            return RedirectResponse(f"/projects/{project_id}", 302)

        # 查詢此前是否已上傳過任何版本
        cur.execute("""
            SELECT id FROM deliveries
            WHERE project_id=%s AND freelancer_id=%s
        """, (project_id, user["id"]))
        existing_deliveries = cur.fetchall()

        # 非退件狀態 → 不可重複上傳
        if existing_deliveries and proj_status != 'reopened':
            return RedirectResponse(f"/projects/{project_id}?filedup=1", 302)

    # --------------- 儲存檔案（不覆蓋舊檔案）-----------------

    # 用 UUID 產生唯一檔名，避免覆蓋舊檔案
    unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
    dest_path = UPLOAD_DIR / unique_filename

    with open(dest_path, "wb") as f:
        f.write(await file.read())

    # 新版本 = 新增一筆紀錄，不刪除任何舊的！
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            INSERT INTO deliveries (project_id, freelancer_id, filename, note)
            VALUES (%s, %s, %s, %s)
        """, (project_id, user["id"], unique_filename, note))
        conn.commit()

    # 如果專案是退件狀態 → 上傳新版後自動回到進行中
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

        # ⭐ 不刪任何 upload，也不刪 deliveries
        # ⭐ 只把專案狀態改成 reopened（允許接案人上傳新版本）

        cur.execute("""
            UPDATE projects
            SET status='reopened'
            WHERE id=%s
        """, (project_id,))
        conn.commit()

    return RedirectResponse(f"/projects/{project_id}", 302)


@app.post("/bids/{project_id}")
def create_bid(
    request: Request,
    project_id: int,
    price: int = Form(...),
    message: str = Form(""),
    proposal_file: UploadFile | None = File(None),
):
    user = current_user(request)
    if not user:
        return RedirectResponse("/login", 302)
    if user["role"] != "freelancer":
        return RedirectResponse(f"/projects/{project_id}", 302)

    from datetime import datetime

    with get_conn() as conn, conn.cursor() as cur:

        # 取得 deadline
        cur.execute("SELECT deadline FROM projects WHERE id=%s", (project_id,))
        row = cur.fetchone()
        deadline = row[0] if row else None

        if deadline and datetime.now() > deadline:
            return RedirectResponse(f"/projects/{project_id}?closed=1", 302)

        # 防止重複報價
        cur.execute(
            "SELECT 1 FROM bids WHERE project_id=%s AND freelancer_id=%s",
            (project_id, user["id"])
        )
        if cur.fetchone():
            return RedirectResponse(f"/projects/{project_id}?dup=1", 302)

        # ⭐ 這兩個欄位要寫入 DB
        proposal_filename = None             # 系統命名
        proposal_original_name = None        # 使用者上傳的原始檔名

        # 處理 PDF
        if proposal_file and proposal_file.filename:

            # 存使用者原始檔名
            proposal_original_name = proposal_file.filename  

            filename = proposal_file.filename.lower()

            # 副檔名檢查
            if not filename.endswith(".pdf"):
                return RedirectResponse(f"/projects/{project_id}?pdf=0", status_code=303)

            # MIME TYPE 檢查
            if proposal_file.content_type != "application/pdf":
                return RedirectResponse(f"/projects/{project_id}?pdf=0", status_code=303)

            # uploads 目錄
            upload_dir = os.path.join("www", "uploads")
            os.makedirs(upload_dir, exist_ok=True)

            # 🔥 使用 UUID 產生唯一檔名
            unique_id = uuid.uuid4().hex
            proposal_filename = f"proposal_{project_id}_{user['id']}_{unique_id}.pdf"

            file_path = os.path.join(upload_dir, proposal_filename)

            # 寫檔
            with open(file_path, "wb") as f:
                f.write(proposal_file.file.read())

        # ⭐⭐ 寫入 DB（新增 proposal_original_name）
        cur.execute("""
            INSERT INTO bids (
                project_id,
                freelancer_id,
                price,
                message,
                proposal_filename,
                proposal_original_name
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            project_id,
            user["id"],
            price,
            message,
            proposal_filename,
            proposal_original_name
        ))

        conn.commit()

    return RedirectResponse(f"/projects/{project_id}?bid_uploaded=1", status_code=303)

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
