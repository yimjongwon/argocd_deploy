from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import uuid
import shutil

app = FastAPI()

# 환경변수 셋팅
WRITABLE_URL = os.getenv("WRITABLE_URL", "postgresql://scott:tiger@localhost:5432/scott_db")
READONLY_URL = os.getenv("READONLY_URL", "postgresql://scott:tiger@localhost:5433/scott_db")

# K8s에서 EFS가 마운트될 경로 (미리 폴더가 있어야 함)
# 환경변수에서 읽어와서 사용하는데 만일 환경변수값이 존재 하지 않으면 기본값 "/mnt/efs/images" 경로 사용하기
EFS_MOUNT_PATH = os.getenv("EFS_MOUNT_PATH", "C:/개발자가 설정한 local 경로")
# exist_ok=True "있으면 그냥 넘어가라"
os.makedirs(EFS_MOUNT_PATH, exist_ok=True)

# ---------------------------------------------------------
# [참고] DB 테이블 생성 스크립트 (사전에 DB에 실행되어 있어야 함)
# CREATE TABLE image_info (
#     img_id SERIAL PRIMARY KEY,
#     original_name VARCHAR(255) NOT NULL,
#     saved_name VARCHAR(255) NOT NULL,
#     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
# );
# ---------------------------------------------------------
SERVICE = "image-backend"

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# 이 부분을 반드시 추가해야 프론트엔드 서비스와 통신이 가능합니다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Image Microservice is running!"}

# [1] 이미지 목록 조회 API
@app.get("/images")
def get_image_list():
    conn = psycopg2.connect(READONLY_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cursor.execute("SELECT img_id, original_name, created_at FROM image_info ORDER BY img_id DESC;")
        rows = cursor.fetchall()
        return {"status": "success", "data": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

# [2] 이미지 업로드 API (EFS에 저장 + DB에 기록)
@app.post("/images")
def upload_image(file: UploadFile = File(...)):
    # 1. 파일명 중복 방지를 위한 UUID 생성
    file_extension = file.filename.split(".")[-1]
    saved_filename = f"{uuid.uuid4().hex}.{file_extension}"
    file_path = os.path.join(EFS_MOUNT_PATH, saved_filename)
    
    # 2. EFS 마운트 경로에 실제 파일 저장
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File save error: {str(e)}")

    # 3. DB에 메타데이터 저장
    conn = psycopg2.connect(WRITABLE_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute(
            "INSERT INTO image_info (original_name, saved_name) VALUES (%s, %s) RETURNING *;",
            (file.filename, saved_filename)
        )
        new_image = cursor.fetchone()
        conn.commit()
    except Exception as e:
        conn.rollback()
        # DB 저장 실패 시, EFS에 올라간 파일도 삭제해주는 것이 좋습니다 (정합성 유지)
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")
    finally:
        cursor.close()
        conn.close()
        
    return {"status": "success", "data": new_image}

# [3] 단일 이미지 보기 API (HTML <img src="..."> 용도)
@app.get("/images/{img_id}")
def get_image(img_id: int):
    conn = psycopg2.connect(READONLY_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cursor.execute("SELECT saved_name FROM image_info WHERE img_id = %s;", (img_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Image not found in DB")
            
        file_path = os.path.join(EFS_MOUNT_PATH, row["saved_name"])
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found in EFS storage")
            
        # FileResponse를 사용하면 FastAPI가 Content-Type을 이미지로 자동 설정하여 반환합니다.
        return FileResponse(file_path)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@app.get("/health")
def health():
    return {"service":SERVICE, "message":"image-backend service is running"}