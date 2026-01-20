# Claude Proxy Server

FastAPI 기반 로컬 프록시 서버로, Anthropic API 요청을 중계합니다. Docker 컨테이너로 쉽게 배포할 수 있습니다.

## 기능

- Anthropic API 프록시 (`/api/anthropic/*`)
- 헬스 체크 엔드포인트
- ntfy를 통한 에러 알림 (선택)
- Docker/Docker Compose 지원

## 빠른 시작

### Docker Compose 사용 (권장)

```bash
# 빌드 및 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 중지
docker-compose down
```

### Docker 직접 사용

```bash
# 이미지 빌드
docker build -t claude-proxy .

# 컨테이너 실행
docker run -d --name claude-proxy -p 3000:3000 claude-proxy

# 컨테이너 중지
docker stop claude-proxy
```

## 엔드포인트

| 경로 | 메서드 | 설명 |
|------|--------|------|
| `/` | GET | 서버 정보 |
| `/health` | GET | 헬스 체크 |
| `/api/anthropic/*` | ALL | Anthropic API 프록시 |

## 환경 변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `BASE_URL` | `https://api.z.ai/api/anthropic` | 타겟 API URL |
| `NTFY_TOPIC` | (없음) | ntfy 알림 토픽 이름 |
| `NTFY_SERVER` | `https://ntfy.sh` | ntfy 서버 주소 |

### 환경 변수 설정 예시

**docker-compose.yml:**
```yaml
environment:
  - BASE_URL=https://api.z.ai/api/anthropic
  - NTFY_TOPIC=your-topic-name
```

**docker run:**
```bash
docker run -d --name claude-proxy -p 3000:3000 \
  -e BASE_URL=https://api.z.ai/api/anthropic \
  -e NTFY_TOPIC=your-topic-name \
  claude-proxy
```

## 사용 예시

```bash
# 헬스 체크
curl http://localhost:3000/health

# 서버 정보
curl http://localhost:3000/

# Anthropic API 프록시
curl -X POST http://localhost:3000/api/anthropic/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: your-key" \
  -d '{"model": "claude-3-5-sonnet-20241022", "max_tokens": 1024, "messages": [{"role": "user", "content": "Hello"}]}'
```

## ntfy 알림 설정

에러 발생 시 푸시 알림을 받으려면 `NTFY_TOPIC` 환경 변수를 설정하세요:

```bash
docker run -d --name claude-proxy -p 3000:3000 \
  -e NTFY_TOPIC=my-claude-proxy \
  claude-proxy
```

## 프로젝트 구조

```
.
├── proxy.py              # FastAPI 애플리케이션
├── requirements.txt      # Python 의존성
├── Dockerfile           # Docker 이미지 빌드 정의
├── docker-compose.yml   # Docker Compose 설정
└── README.md            # 이 파일
```

## 의존성

- FastAPI 0.128+
- Uvicorn (ASGI 서버)
- httpx (HTTP 클라이언트)
- gunicorn (WSGI 서버, 선택)

## 라이선스

MIT
