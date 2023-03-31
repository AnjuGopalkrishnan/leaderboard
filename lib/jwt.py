from __future__ import annotations

from datetime import datetime, timedelta
from jose import jwt,JWTError
from fastapi import Depends, status, HTTPException
from fastapi.security import OAuth2PasswordBearer

import infra.db
from infra import db
from sqlalchemy.orm import Session


SECRET_KEY = "b94f8e6272fcef848060d16721461f19439147462768dadfaf9e132b5e7d5dca"
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/v1/user/login')


def create_access_token(payload: dict, expires_delta: timedelta | None = None):
    payload_copy = payload.copy()
    if expires_delta:
        expires = datetime.utcnow() + expires_delta
    else:
        expires = datetime.utcnow() + timedelta(minutes=60)
    payload_copy.update({"exp": expires})
    token = jwt.encode(payload_copy, SECRET_KEY, algorithm=ALGORITHM)
    return token


def decode_token(token: str):
    return jwt.decode(token, SECRET_KEY, ALGORITHM)


def verify_access_token(token: str, credentials_exception):

    try:
        payload = decode_token(token)
        print(payload)
        id: str = payload.get("username")
        if id is None:
            raise credentials_exception
        token_data = id
    except JWTError:
        raise credentials_exception

    return token_data

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(db.get_db)):
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                          detail=f"Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})

    token = verify_access_token(token, credentials_exception)
    user = db.query(infra.db.User).filter(infra.db.User.username == token).first()

    return user