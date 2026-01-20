프로덕션 문서:
FastAPI 로컬 프록시 서버 – Docker 배포 문서

이 문서는 로컬 프록시 서버를 FastAPI로 구현한 프로젝트를 Docker 컨테이너로 배포하는 방법을 설명합니다. PM2 대신 Docker를 사용하면 사용자가 컨테이너를 쉽게 실행/중지하고, 환경을 재현하기 쉬운 이점이 있습니다. 아래 지침을 따르면 프록시 서버를 프로덕션 환경에서 안정적으로 운영할 수 있습니다.

1. 프로젝트 개요

프록시 서버는 proxy.py에 정의된 FastAPI 애플리케이션으로, /api/anthropic/* 경로의 요청을 외부 Anthropic API(https://api.z.ai/api/anthropic)로 전달합니다. 의존성은 fastapi, uvicorn, httpx이며, 이전 README에서 다룬 ntfy 알림 기능도 포함되어 있습니다. 이 문서에서는 이러한 코드를 Docker 이미지로 빌드하고 실행하는 방법을 안내합니다.

2. 디렉터리 구조

컨테이너화를 위해 프로젝트 루트에 다음과 같은 파일을 준비합니다:

.
├── proxy.py         # FastAPI 애플리케이션 (프록시 구현)
├── requirements.txt # Python 의존성 목록
├── Dockerfile       # Docker 이미지 빌드 정의
└── docker-compose.yml (선택) # 여러 컨테이너를 쉽게 관리하려면


requirements.txt는 다음과 같이 구성합니다:

fastapi
uvicorn
httpx

3. Dockerfile 작성

Dockerfile은 Python 공식 이미지를 기반으로 하고, 의존성 파일을 먼저 복사한 후 애플리케이션 코드를 복사합니다. FastAPI 공식 가이드에서는 CMD를 exec form으로 작성해야 애플리케이션이 우아하게 종료되고 라이프사이클 이벤트가 제대로 동작한다고 강조합니다. 아래는 예시 Dockerfile입니다:

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
CMD ["fastapi", "run", "/app/proxy.py", "--host", "0.0.0.0", "--port", "3000"]


위 예시에서 CMD는 리스트 형태의 exec form이며, fastapi run 명령을 사용해 proxy.py를 직접 실행합니다. FastAPI 문서는 쉘 형식(CMD fastapi run ...) 대신 exec 형식을 사용할 것을 권장합니다.

옵션: Gunicorn + Uvicorn Workers

프로덕션 환경에서 더 높은 성능과 안정성을 위해 gunicorn과 uvicorn worker를 함께 사용할 수도 있습니다. 예를 들어 다음과 같은 CMD를 사용할 수 있습니다:

CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "2", "proxy:app", "-b", "0.0.0.0:3000"]


단, 이 경우 gunicorn을 의존성에 포함해야 하며, 애플리케이션 이름(proxy:app)이 정확해야 합니다.

4. Docker 이미지 빌드

모든 파일이 준비되면 프로젝트 루트에서 다음 명령으로 Docker 이미지를 빌드합니다. FastAPI 문서에서는 현재 디렉터리를 빌드 컨텍스트로 지정하기 위해 마지막에 .을 붙여야 한다고 설명합니다.

docker build -t claude-proxy .


이 명령은 Dockerfile을 읽어 claude-proxy라는 이름의 이미지를 생성합니다. 빌드 과정에서 requirements.txt를 먼저 복사하여 Docker 캐시를 활용함으로써 재빌드 시간을 단축할 수 있습니다.

5. 컨테이너 실행

이미지 빌드 후 다음 명령으로 컨테이너를 실행합니다. FastAPI 문서에 따르면 docker run -d --name <컨테이너명> -p <호스트포트>:<컨테이너포트> <이미지> 형식으로 실행할 수 있습니다.

docker run -d --name claude-proxy -p 3000:3000 claude-proxy


이렇게 하면 컨테이너가 백그라운드(-d)에서 실행되며, 호스트의 3000번 포트를 컨테이너 내부의 3000번 포트에 매핑합니다. 브라우저에서 http://localhost:3000으로 접속해 프록시를 사용할 수 있습니다.

컨테이너를 중지하려면:

docker stop claude-proxy


컨테이너를 다시 시작하려면:

docker start claude-proxy


컨테이너를 완전히 삭제하려면:

docker rm -f claude-proxy

6. docker-compose 사용 (선택 사항)

여러 환경 변수가 필요하거나 여러 컨테이너를 함께 관리하려면 docker-compose.yml을 사용하면 편리합니다. 예를 들어 다음과 같이 작성할 수 있습니다:

version: '3.8'
services:
  claude-proxy:
    build: .
    container_name: claude-proxy
    ports:
      - "3000:3000"
    environment:
      # 필요에 따라 Anthropic API 기본 URL을 프록시로 변경
      - ANTHROPIC_BASE_URL=http://127.0.0.1:3000/api/anthropic
    restart: unless-stopped


이후 다음 명령으로 컨테이너를 빌드 및 실행할 수 있습니다:

docker-compose up -d


컨테이너를 중지하려면:

docker-compose down


restart: unless-stopped 옵션은 컨테이너가 비정상적으로 종료되면 자동으로 재시작하도록 설정합니다. 필요에 따라 always로 변경할 수 있습니다.

7. 환경 변수 및 프록시 설정

프록시 서버 코드(proxy.py)는 기본적으로 https://api.z.ai/api/anthropic을 외부 API로 사용합니다. 만약 클라이언트 코드에서 ANTHROPIC_BASE_URL을 지정할 수 없을 경우, 컨테이너 실행 시 환경 변수를 사용하거나 BASE_URL 변수를 수정할 수 있습니다. 예를 들어, 컨테이너 실행 시 환경 변수로 전달하려면:

docker run -d --name claude-proxy -p 3000:3000 \
  -e BASE_URL=https://api.z.ai/api/anthropic claude-proxy


또는 애플리케이션 코드에서 BASE_URL 값을 수정하여 다른 엔드포인트를 타겟팅할 수 있습니다.

8. 참고 사항

TLS 종단 프록시: 로드 밸런서나 프록시 서버(Nginx, Traefik 등) 뒤에 컨테이너를 배포하는 경우 --proxy-headers 옵션을 추가하면 FastAPI가 원본 요청의 프로토콜/호스트 정보를 신뢰하도록 할 수 있습니다.

프록시 알림: ntfy CLI가 설치되어 있고 토픽이 설정되어 있다면, proxy.py에서 오류 발생 시 푸시 알림을 받을 수 있습니다. Dockerfile에 ntfy 설치를 포함할 수도 있지만, 보안상의 이유로 호스트 환경에서 관리하는 것이 일반적입니다.

Docker 캐시 활용: 의존성 파일을 먼저 복사하고 설치하는 구조는 Docker 빌드 캐시를 활용해 빌드 시간을 단축합니다.

9. 출처

FastAPI 공식 문서 – FastAPI in Containers - Docker: Dockerfile 작성, exec form 사용, 이미지 빌드 및 컨테이너 실행에 관한 권장 사항을 제공합니다.

FastAPI 공식 문서 – Server Workers - Uvicorn with Workers: 생산 환경에서 Gunicorn과 Uvicorn 워커 조합 사용을 안내합니다 (문서에서 구체적인 코드 예시는 제공되지 않지만, Uvicorn worker 사용을 제안합니다).

이 문서를 참고하여 로컬 프록시 서버를 Docker 컨테이너로 배포하면, 사용자는 단일 명령어로 쉽게 컨테이너를 실행하고 중지할 수 있습니다. 궁금한 점이 있으면 언제든 질문해 주세요.