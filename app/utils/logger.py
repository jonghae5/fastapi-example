import json
import logging
from datetime import timedelta, datetime
from time import time
from fastapi.requests import Request
from fastapi import Body

from fastapi.logger import logger

logger.setLevel(logging.INFO)


async def api_logger(request: Request, response=None, error=None):
    time_format = "%Y/%m/%d %H:%M:%S"
    t = time() - request.state.start
    status_code = error.status_code if error else response.status_code
    error_log = None
    user = request.state.user
    # body 에 무엇이 들어가 있는지 확인
    # body = await request.body()
    # 에러가 있을 때
    if error:
        # inspect 가 있으면, 코드 확인
        if request.state.inspect:
            frame = request.state.inspect
            error_file = frame.f_code.co_filename
            error_func = frame.f_code.co_name
            error_line = frame.f_lineno
        # 확인 불가
        else:
            error_func = error_file = error_line = "UNKNOWN"

        error_log = dict(
            errorFunc=error_func,
            location="{} line in {}".format(str(error_line), error_file),
            raised=str(error.__class__.__name__),
            msg=str(error.ex),
        )

    email = user.email.split("@") if user and user.email else None
    user_log = dict(
        client=request.state.ip,
        user=user.id if user and user.id else None,
        email="**" + email[0][2:-1] + "*@" + email[1] if user and user.email else None,
    )

    log_dict = dict(
        url=request.url.hostname + request.url.path,
        method=str(request.method),
        statusCode=status_code,
        errorDetail=error_log,
        client=user_log,
        processedTime=str(round(t * 1000, 5)) + "ms",
        datetimeUTC=datetime.utcnow().strftime(time_format),
        datetimeKST=(datetime.utcnow() + timedelta(hours=9)).strftime(time_format),
    )
    # if body:
    #     log_dict["body"] = body
    if error and error.status_code >= 500:
        logger.error(json.dumps(log_dict))
    else:
        logger.info(json.dumps(log_dict))