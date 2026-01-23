"""
FastAPI 로컬 프록시 서버

Anthropic API 요청을 프록시하여 외부 API로 전달합니다.
"""
import os
from typing import Dict, Any

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse

# 환경 변수 설정
BASE_URL = os.getenv("BASE_URL", "https://api.z.ai/api/anthropic")
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "")
NTFY_SERVER = os.getenv("NTFY_SERVER", "https://ntfy.sh")

# 타임아웃 설정 (스트리밍: 300초, 연결: 10초)
STREAM_TIMEOUT = httpx.Timeout(300.0, connect=10.0)

app = FastAPI(
    title="Claude Proxy Server",
    description="Anthropic API 로컬 프록시 서버",
    version="1.0.0",
)


async def send_ntfy_notification(message: str, priority: str = "urgent") -> None:
    """
    ntfy를 통해 푸시 알림을 전송합니다.

    Args:
        message: 전송할 메시지
        priority: 알림 우선순위 (default, urgent, etc.)
    """
    if not NTFY_TOPIC:
        return

    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{NTFY_SERVER}/{NTFY_TOPIC}",
                content=message.encode("utf-8"),
                headers={"Priority": priority}
            )
    except Exception as e:
        # 알림 전송 실패는 로그만 남기고 계속 진행
        print(f"Failed to send ntfy notification: {e}")


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """헬스 체크 엔드포인트"""
    return {"status": "healthy", "proxy_target": BASE_URL}


def is_stream_request(body: bytes) -> bool:
    """요청 바디에서 stream: true 확인"""
    if not body:
        return False
    try:
        import json
        data = json.loads(body.decode("utf-8"))
        return data.get("stream", False) is True
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False


def build_target_url(path: str, query: str) -> str:
    """타겟 URL 구성"""
    target_url = f"{BASE_URL}/{path}"
    if query:
        target_url += f"?{query}"
    return target_url


def filter_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """요청 헤더에서 hop-by-hop 헤더 제거"""
    filtered = dict(headers)
    for key in ["host", "Host"]:
        filtered.pop(key, None)
    return filtered


def filter_response_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """응답 헤더에서 전달하면 안 되는 항목 제거"""
    filtered = dict(headers)
    for key in [
        "content-length",
        "Content-Length",
        "content-encoding",
        "Content-Encoding",
        "transfer-encoding",
        "Transfer-Encoding",
    ]:
        filtered.pop(key, None)
    return filtered


async def stream_upstream(
    method: str,
    url: str,
    headers: Dict[str, str],
    body: bytes,
):
    """업스트림 서버와 스트리밍 통신"""
    async with httpx.AsyncClient(timeout=STREAM_TIMEOUT) as client:
        async with client.stream(
            method=method,
            url=url,
            headers=headers,
            content=body,
        ) as response:
            # 먼저 상태 코드와 헤더를 yield
            response_headers = filter_response_headers(dict(response.headers))

            yield {"status_code": response.status_code, "headers": response_headers}

            # 청크 단위로 데이터 전달
            async for chunk in response.aiter_bytes():
                if chunk:
                    yield chunk


@app.api_route("/api/anthropic/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_anthropic(request: Request, path: str) -> Response:
    """
    Anthropic API 요청을 프록시합니다.
    """
    body = await request.body()
    headers = filter_headers(dict(request.headers))
    target_url = build_target_url(path, request.url.query)
    is_streaming = is_stream_request(body)

    try:
        if is_streaming:
            # 스트리밍 요청 처리
            stream_gen = stream_upstream(request.method, target_url, headers, body)

            # 첫 번째 yield에서 메타데이터 추출
            meta = await stream_gen.__anext__()

            async def generate():
                try:
                    async for chunk in stream_gen:
                        yield chunk
                except Exception as e:
                    error_msg = f"Streaming interrupted: {str(e)}"
                    print(f"Error during streaming: {e}")
                    await send_ntfy_notification(f"Claude Proxy Stream Error: {error_msg}")
                    raise e

            return StreamingResponse(
                generate(),
                status_code=meta["status_code"],
                headers=meta["headers"],
            )
        else:
            # 일반 요청 처리
            timeout = httpx.Timeout(120.0, connect=60.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(
                    method=request.method,
                    url=target_url,
                    headers=headers,
                    content=body,
                )

                response_headers = filter_response_headers(dict(response.headers))

                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=response_headers,
                )

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP error: {e.response.status_code} - {str(e)}"
        await send_ntfy_notification(f"Claude Proxy Error: {error_msg}")
        return Response(
            content=error_msg.encode("utf-8"),
            status_code=e.response.status_code,
        )

    except httpx.RequestError as e:
        error_msg = f"Request error: {str(e)}"
        await send_ntfy_notification(f"Claude Proxy Error: {error_msg}")
        return Response(
            content=error_msg.encode("utf-8"),
            status_code=503,
        )

    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        await send_ntfy_notification(f"Claude Proxy Error: {error_msg}")
        return Response(
            content=error_msg.encode("utf-8"),
            status_code=500,
        )


@app.get("/")
async def root() -> Dict[str, Any]:
    """루트 엔드포인트 - 서버 정보 반환"""
    return {
        "name": "Claude Proxy Server",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "proxy": "/api/anthropic/*"
        },
        "environment": {
            "base_url": BASE_URL,
            "ntfy_configured": bool(NTFY_TOPIC)
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
