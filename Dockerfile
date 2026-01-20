# Python 3.11 슬림 이미지를 사용
FROM python:3.11-slim

# 애플리케이션 작업 디렉터리 설정
WORKDIR /app

# 의존성 파일만 먼저 복사하여 캐시 활용
COPY requirements.txt /app/requirements.txt

# 의존성 설치 (캐시 사용)
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

# 애플리케이션 코드 복사
COPY proxy.py /app/proxy.py

# 컨테이너 내에서 FastAPI 앱 실행 (exec form 사용)
CMD ["uvicorn", "proxy:app", "--host", "0.0.0.0", "--port", "3000"]
