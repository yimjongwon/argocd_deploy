# 1. 가벼운 파이썬 공식 이미지 사용
FROM python:3.11-slim

# 2. 작업 디렉토리 설정
WORKDIR /app

# 3. 종속성 파일 먼저 복사 (캐시 최적화)
COPY requirements.txt .

# 4. 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt

# 5. Index 서비스 소스 코드 복사
COPY src/ .

# 6. 8000 port 를 사용한다고 명시하기
EXPOSE 8000

# 7. FastAPI 실행 (Uvicorn 사용)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]