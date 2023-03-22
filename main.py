from fastapi import FastAPI, Request, HTTPException
from starlette.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
import infra.db
from lib import jwt

import lib.authenticate
from infra import models

templates = Jinja2Templates(directory="templates")

app = FastAPI()
app.mount("/static", StaticFiles(directory="static", html=True), name="static")


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})



@app.get("/login/login.html")
def home(request: Request):
    return templates.TemplateResponse("login/login.html", {"request": request})

@app.get("/login/register.html")
def home(request: Request):
    return templates.TemplateResponse("login/register.html", {"request": request})


@app.post("/v1/users/register")
def register(user: models.User):
    print(user)
    hashPwd = lib.authenticate.get_password_hash(user.password)
    values = {
        'username': user.username,
        'password': hashPwd
    }
    query = text("INSERT INTO users(user_name, password) VALUES(:username, :password)")
    with infra.db.engine.begin() as conn:
        res = conn.execute(query, values)

    if res:
        return {
            "username": user.username,
            "register_success": True
        }
    return {
        "register_success": False
    }


@app.post("/v1/user/login")
def login(user: models.User):
    values = {
        'username': user.username,
    }
    query = text("SELECT * FROM users WHERE user_name = :username LIMIT 1")
    with infra.db.engine.begin() as conn:
        res = conn.execute(query, values)

    if not res:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
        )
    for row in res:
        if not lib.authenticate.verify_password(user.password, row[1]):
            raise HTTPException(
                status_code=401,
                detail="Incorrect username or password",
            )
    access_token = jwt.create_access_token(payload={"username":user.username})
    return {"access_token":access_token}


@app.get("/v1/user/{id}/hosted")
def hosted(id):
    query = infra.db.competitions.select().where(infra.db.competitions.c.host_user_id == id)
    with infra.db.engine.begin() as conn:
        res = conn.execute(query)

    ansDict = []
    for idx, row in enumerate(res):
        tempDict = {}
        for idx, key in enumerate(res.keys()):
            tempDict[key] = row[idx]
        ansDict.append(tempDict)

    return ansDict


@app.get("/v1/user/{id}/competitions")
def getcompetitions(id):
    query = infra.db.submissions.select().where(infra.db.submissions.c.user_id == id)
    with infra.db.engine.begin() as conn:
        res = conn.execute(query)

    compIds = []
    for idx, row in enumerate(res):
        compIds.append(row[0])

    query2 = infra.db.competitions.select().where(infra.db.competitions.c.c_id.in_(compIds))
    with infra.db.engine.begin() as conn:
        res = conn.execute(query2)

    ansDict = []
    for idx, row in enumerate(res):
        tempDict = {}
        for idx, key in enumerate(res.keys()):
            tempDict[key] = row[idx]
        ansDict.append(tempDict)

    return ansDict
