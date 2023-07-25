import time
import jwt
import base64
import hmac

from jwt.exceptions import ExpiredSignatureError, DecodeError
import sqlalchemy
from starlette.requests import Request
from starlette.datastructures import URL, Headers
from starlette.responses import PlainTextResponse, RedirectResponse, Response, JSONResponse

from app.database.conn import db
from app.database.schema import Users, ApiKeys

from app.common.consts import EXCEPT_PATH_LIST, EXCEPT_PATH_REGEX
from app.utils.logger import api_logger

import re
from app.common import config, consts

from app.models import UserToken
from app.errors import exceptions as ex
from app.errors.exceptions import APIException, SqlFailureEx, APIQueryStringEx

from app.utils.date_utils import D
from app.utils.query_utils import to_dict

async def access_control(request: Request, call_next):
    # 요청시간
    request.state.req_time = D.datetime()
    # 처리 시간 시작
    request.state.start = time.time()
    # Handling이 안되는 Error Logging
    # Sentry를 사용해도 됨
    request.state.inspect = None
    # Token Decode한 내용을 넣을 Data
    # 가장 큰 목적 : DB에 넣지 않고, User의 인증 유무 및 데이터를 확인 가능 (필수 정보)
    request.state.user = None
    request.state.service = None

    # AWS 경우, LB를 지날 때, 고객 IP를 아래에 넣어줌.
    ip = request.headers["x-forwarded-for"] if "x-forwarded-for" in request.headers.keys() else request.client.host
    request.state.ip = ip.split(",")[0] if "," in ip else ip
    headers = request.headers
    cookies = request.cookies
    url = request.url.path

    if await url_pattern_check(url, EXCEPT_PATH_REGEX) or url in EXCEPT_PATH_LIST:
        # 다음 요청으로 이동
        response = await call_next(request)
        if url != "/":
            await api_logger(request=request, response=response)
        return response
    try:
        if url.startswith("/api"):
            # api 인경우 헤더로 토큰 검사
            if url.startswith("/api/services"):
                qs = str(request.query_params)
                qs_list = qs.split("&")
                session = next(db.session())

                # Prod 일 때
                if not config.conf().DEBUG:
                    # 쿼리 스트링이 올바르게 오지 않은 경우
                    try:
                        qs_dict = {qs_split.split("=")[0]: qs_split.split("=")[1] for qs_split in qs_list}
                    except Exception:
                        raise ex.APIQueryStringEx()
                    qs_keys = qs_dict.keys()
                    # 쿼리 스트링에 key 값이 key, timestamp 가 없는 경우
                    if "key" not in qs_keys or "timestamp" not in qs_keys:
                        raise ex.APIQueryStringEx()

                    # header key에 secret가 없는 경우
                    if "secret" not in headers.keys():
                        raise ex.APIHeaderInvalidEx()

                    api_key = ApiKeys.get(session=session, access_key=qs_dict["key"])
                    if not api_key:
                        raise ex.NotFoundAccessKeyEx(api_key=qs_dict["key"])

                    # hmac 모듈로 Hashing(단방향) -> key와 timestamp를 바꾸고, 이후에 header에 있는 해싱 키랑 항상 비교
                    mac = hmac.new(bytes(api_key.secret_key, encoding='utf8'), bytes(qs, encoding='utf-8'),
                                   digestmod='sha256')
                    d = mac.digest()
                    validating_secret = str(base64.b64encode(d).decode('utf-8'))

                    if headers["secret"] != validating_secret:
                        raise ex.APIHeaderInvalidEx()

                    # 10초 내에 만들어진 요청만 Validation -> Replay Attack 방지
                    now_timestamp = int(D.datetime(diff=9).timestamp())
                    if now_timestamp - 10 > int(qs_dict["timestamp"]) or now_timestamp < int(qs_dict["timestamp"]):
                        raise ex.APITimestampEx()
                    # Lazy 하다.
                    user_info = to_dict(api_key.users)
                    request.state.user = UserToken(**user_info)
                else:
                    # Request User 가 필요함
                    # authorization? Authorization
                    if "authorization" in headers.keys():
                        key = headers.get("Authorization")
                        api_key_obj = ApiKeys.get(session=session, access_key=key)
                        user_info = to_dict(Users.get(session=session, id=api_key_obj.user_id))
                        request.state.user = UserToken(**user_info)
                        # 토큰 없음
                    else:
                        if "Authorization" not in headers.keys():
                            raise ex.NotAuthorized()
                # 실제로 계속 세션을 생성하면, 병목현상이 일어남. -> redis 나 Cache Storage를 사용하자.
                # 기존 세션을 생성해서 위 user_info 가 불러질 때까지 세션을 유지해야 해서 아래에 session.close()
                session.close()
                response = await call_next(request)
                return response
                # 토큰 없음
            else:

                if "authorization" in headers.keys():
                    token_info = await token_decode(access_token=headers.get("Authorization"))
                    request.state.user = UserToken(**token_info)
                    # 토큰 없음
                else:
                    if "Authorization" not in headers.keys():
                        raise ex.NotAuthorized()
        else:
            # 템플릿 렌더링인 경우 쿠키에서 토큰 검사
            # Pycharm에 등록 env key
            cookies["Authorization"] = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6MSwiZW1haWwiOiJkaHdoZGdvMjM2OEBnbWFpbC5jb20iLCJuYW1lIjpudWxsLCJwaG9uZV9udW1iZXIiOm51bGwsInByb2ZpbGVfaW1nIjpudWxsLCJzbnNfdHlwZSI6bnVsbH0.-k7ZHjvw1Uo7es3wxzM0rBozfqTRj2XPJBJZuYxL53M"
            if "Authorization" not in cookies.keys():
                raise ex.NotAuthorized()

            token_info = await token_decode(access_token=cookies.get("Authorization"))
            request.state.user = UserToken(**token_info)

        response = await call_next(request)
        await api_logger(request=request, response=response)
        return response

    except Exception as e:
        error = await exception_handler(e)
        error_dict = dict(status=error.status_code, msg=error.msg, detail=error.detail, code=error.code)

        response = JSONResponse(status_code=error.status_code, content=error_dict)
        await api_logger(request=request, error=error)
        return response

async def url_pattern_check(path, pattern):

    result = re.match(pattern, path)
    if result:
        return True
    return False


async def token_decode(access_token):
    """
    :param access_token:
    :return:
    """
    try:
        access_token = access_token.replace("Bearer ", "")
        payload = jwt.decode(access_token, key=consts.JWT_SECRET, algorithms=[consts.JWT_ALGORITHM])
    except ExpiredSignatureError:
        raise ex.TokenExpiredEx()
    except DecodeError:
        raise ex.TokenDecodeEx()
    return payload


async def exception_handler(error: Exception):
    print(error)

    if isinstance(error, sqlalchemy.exc.OperationalError):
        error = SqlFailureEx(ex=error)
    if not isinstance(error, APIException):
        error = APIException(ex=error, detail=str(error))
    return error