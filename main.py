import os
import uuid
import shutil
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import asc

from config import UPLOAD_DIR, SCHEDULE_HOUR, SCHEDULE_MINUTE
from models import SessionLocal, PostQueue
from naver_blog import NaverBlogPoster


def publish_post(post: PostQueue):
    """단일 포스트 발행"""
    poster = NaverBlogPoster()
    try:
        poster.login()

        image_paths = [p.strip() for p in post.image_paths.split(",") if p.strip()] if post.image_paths else []
        tags = [t.strip() for t in post.tags.split(",") if t.strip()] if post.tags else []

        poster.post(
            title=post.title,
            content=post.content,
            category=post.category,
            tags=tags,
            image_paths=image_paths,
        )

        post.is_published = True
        post.published_at = datetime.now()
        post.error_message = None
    except Exception as e:
        post.error_message = str(e)
    finally:
        poster.close()


def scheduled_publish():
    """스케줄러: 큐에서 가장 오래된 미발행 글을 발행"""
    db = SessionLocal()
    try:
        post = (
            db.query(PostQueue)
            .filter(PostQueue.is_published == False)
            .order_by(asc(PostQueue.created_at))
            .first()
        )
        if not post:
            print(f"[{datetime.now()}] 발행할 글 없음")
            return

        print(f"[{datetime.now()}] 발행 시작: {post.title}")
        publish_post(post)
        db.commit()
        print(f"[{datetime.now()}] 발행 완료: {post.title} (성공={post.is_published})")
    finally:
        db.close()


# 스케줄러 설정
scheduler = BackgroundScheduler()
scheduler.add_job(
    scheduled_publish,
    "cron",
    hour=SCHEDULE_HOUR,
    minute=SCHEDULE_MINUTE,
    id="daily_publish",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    print(f"스케줄러 시작: 매일 {SCHEDULE_HOUR:02d}:{SCHEDULE_MINUTE:02d}에 자동 발행")
    yield
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    db = SessionLocal()
    queued = (
        db.query(PostQueue)
        .filter(PostQueue.is_published == False)
        .order_by(asc(PostQueue.created_at))
        .all()
    )
    published = (
        db.query(PostQueue)
        .filter(PostQueue.is_published == True)
        .order_by(PostQueue.published_at.desc())
        .limit(10)
        .all()
    )
    db.close()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "queued": queued,
        "published": published,
        "schedule_time": f"{SCHEDULE_HOUR:02d}:{SCHEDULE_MINUTE:02d}",
    })


@app.post("/api/post")
async def create_post(
    title: str = Form(...),
    content: str = Form(...),
    category: str = Form(""),
    tags: str = Form(""),
    action: str = Form("queue"),  # "publish" or "queue"
    images: list[UploadFile] = File(default=[]),
):
    # 이미지 저장
    saved_paths = []
    for img in images:
        if img.filename:
            ext = Path(img.filename).suffix
            filename = f"{uuid.uuid4().hex}{ext}"
            filepath = UPLOAD_DIR / filename
            with open(filepath, "wb") as f:
                shutil.copyfileobj(img.file, f)
            saved_paths.append(str(filepath))

    if action == "publish":
        # 즉시 발행
        post = PostQueue(
            title=title,
            content=content,
            category=category,
            tags=tags,
            image_paths=",".join(saved_paths),
        )
        publish_post(post)

        db = SessionLocal()
        db.add(post)
        db.commit()
        db.close()

        if post.is_published:
            return JSONResponse({"status": "ok", "message": "발행 완료!"})
        else:
            return JSONResponse({"status": "error", "message": post.error_message}, status_code=500)

    else:
        # 예약 큐에 추가
        db = SessionLocal()
        post = PostQueue(
            title=title,
            content=content,
            category=category,
            tags=tags,
            image_paths=",".join(saved_paths),
        )
        db.add(post)
        db.commit()
        db.close()
        return JSONResponse({"status": "ok", "message": "예약 큐에 추가됨!"})


@app.delete("/api/queue/{post_id}")
async def delete_queued(post_id: int):
    db = SessionLocal()
    post = db.query(PostQueue).filter(PostQueue.id == post_id).first()
    if post and not post.is_published:
        db.delete(post)
        db.commit()
    db.close()
    return JSONResponse({"status": "ok"})


@app.post("/api/login-test")
async def login_test():
    """로그인 테스트"""
    poster = NaverBlogPoster()
    try:
        poster.login()
        poster.close()
        return JSONResponse({"status": "ok", "message": "로그인 성공!"})
    except Exception as e:
        poster.close()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
