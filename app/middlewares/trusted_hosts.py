import typing


from starlette.datastructures import URL, Headers
from starlette.responses import PlainTextResponse, RedirectResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

ENFORCE_DOMAIN_WILDCARD = "Domain wildcard patterns must be like '*.example.com'."


class TrustedHostMiddleware:
    """
    except_path 가 없으면, Cloud 내 로트 밸런서에서 내부 IP Health Check를 하지 못한다.
    """

    def __init__(
        self,
        # ASGI(Asynchronous Server Gateway Interface) 애플리케이션에 대한 미들웨어
        app: ASGIApp,
        allowed_hosts: typing.Sequence[str] = None,
        except_path: typing.Sequence[str] = None,
        www_redirect: bool = True,
    ) -> None:
        if allowed_hosts is None:
            allowed_hosts = ["*"]
        if except_path is None:
            except_path = []
        for pattern in allowed_hosts:
            assert "*" not in pattern[1:], ENFORCE_DOMAIN_WILDCARD
            if pattern.startswith("*") and pattern != "*":
                assert pattern.startswith("*."), ENFORCE_DOMAIN_WILDCARD


        self.app = app
        self.allowed_hosts = list(allowed_hosts)
        # ["*"] 인지 확인
        self.allow_any = "*" in allowed_hosts
        self.www_redirect = www_redirect
        self.except_path = list(except_path)

    """
        scope: 현재 요청의 스코프 정보를 가진 딕셔너리
        receive: 요청의 바이트 스트림을 수신하기 위한 코루틴
        send: 응답의 바이트 스트림을 전송하기 위한 코루틴
    """
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        print("Hello Trusted")
        if self.allow_any or scope["type"] not in ("http", "websocket",):  # pragma: no cover
            # 원래의 ASGI 애플리케이션을 호출
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        host = headers.get("host", "").split(":")[0]
        is_valid_host = False
        found_www_redirect = False
        for pattern in self.allowed_hosts:
            if (
                host == pattern
                or (pattern.startswith("*") and host.endswith(pattern[1:]))
                or URL(scope=scope).path in self.except_path
            ):
                is_valid_host = True
                break
            elif "www." + host == pattern:
                found_www_redirect = True

        if is_valid_host:
            await self.app(scope, receive, send)
        else:
            if found_www_redirect and self.www_redirect:
                url = URL(scope=scope)
                redirect_url = url.replace(netloc="www." + url.netloc)
                # "www"로 시작하는 호스트로 리디렉션
                response = RedirectResponse(url=str(redirect_url))  # type: Response
            else:
                response = PlainTextResponse("Invalid host header", status_code=400)

            await response(scope, receive, send)