from typing import Optional
from dataclasses import asdict

from fastapi import FastAPI, Depends
from fastapi.security import APIKeyHeader
import uvicorn

# Base Directory에서 export PYTHONPATH=$PWD 실행 > 절대 경로로 바뀜
from app.common.config import conf
from app.database.conn import db
from app.routes import index, auth, users, example, services


from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

from app.common.consts import EXCEPT_PATH_LIST, EXCEPT_PATH_REGEX

# from app.middlewares.token_validator import AccessControl
from app.middlewares.token_validator import access_control
from app.middlewares.trusted_hosts import TrustedHostMiddleware


# 기본값은 True
# docs 에 Authorization 버튼 추가
API_KEY_HEADER = APIKeyHeader(name="Authorization", auto_error=False)

def create_app():
    """
    앱 함수 실행
    :return:
    """
    app = FastAPI()
    # 데이터 베이스 Initialize
    c = conf()
    conf_dict = asdict(c)
    db.init_app(app, **conf_dict)
    # 레디스 Initialize

    # 미들웨어 정의
    # Stack 프레임 구조로, 제일 밑에 있는 미들웨어부터 검사한다!
    # 중요! Access Token을 제일 나중에 실행 되도록 한다.
    app.add_middleware(middleware_class=BaseHTTPMiddleware, dispatch=access_control)
    # FrontEnd와 BackEnd의 주소가 같아야 통신 가능
    app.add_middleware(
        CORSMiddleware,
        allow_origins=conf().ALLOW_SITE,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Health Check 용 URL /health
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=conf().TRUSTED_HOSTS, except_path=["/health"])

    # 라우터 정의
    app.include_router(index.router)
    # Dependency가 적용되어 있는 API 생성
    app.include_router(users.router, tags=["Users"], prefix="/api", dependencies=[Depends(API_KEY_HEADER)])
    if conf().DEBUG:
        app.include_router(services.router, tags=["Services"], prefix="/api", dependencies=[Depends(API_KEY_HEADER)])
    else:
        app.include_router(services.router, tags=["Services"], prefix="/api")

    app.include_router(auth.router, tags=["Authentication"], prefix="/api")
    app.include_router(example.router, tags=["Example"], prefix="/example")


    return app


app = create_app()

if __name__ == "__main__":
    # uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=conf().PROJ_RELOAD)


#uvicorn main!app --reload