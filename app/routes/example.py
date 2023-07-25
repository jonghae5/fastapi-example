from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse

# TODO:
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from app import models
from app.database.conn import db
from app.database.schema import Users

router = APIRouter()


@router.get("/")
async def ex_hello(session: Session = Depends(db.session)):

    new_user = Users.create(session=session,auto_commit=True, email="dhwhdgo2368@gmail.com", pw="1234")

    return JSONResponse(status_code=200, content={"hello":"world"})
