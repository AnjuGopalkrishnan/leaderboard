import os.path
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, Form, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi import Request
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text, create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy_utils import database_exists, create_database, drop_database
from starlette.templating import Jinja2Templates

import infra.db
import lib.authenticate
from infra import models
from infra.db import User
from lib import jwt

templates = Jinja2Templates(directory="templates")

SCHEMA_PATH = "schemas"
ANS_PATH = "answers"

if not os.path.exists(SCHEMA_PATH):
    os.mkdir(SCHEMA_PATH)

if not os.path.exists(ANS_PATH):
    os.mkdir(ANS_PATH)

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


@app.get("/competition.html")
def home(request: Request):
    return templates.TemplateResponse("competition.html", {"request": request})


@app.get("/onecompetition.html")
def home(request: Request):
    return templates.TemplateResponse("onecompetition.html", {"request": request})


@app.get("/hostcompetition.html")
def home(request: Request):
    return templates.TemplateResponse("hostcompetition.html", {"request": request})


@app.post("/v1/user/register")
def register(user: models.User, db: Session = Depends(infra.db.get_db)):
    hashPwd = lib.authenticate.get_password_hash(user.password)

    new_user = User(username=user.username, password=hashPwd)
    db.add(new_user)
    try:
        db.commit()
        return {
            "username": user.username,
            "register_success": True
        }
    except SQLAlchemyError as e:
        print(e)
        return {
            "register_success": False
        }


@app.post("/v1/user/login")
def login(user: models.User):
    values = {
        'username': user.username,
    }
    query = text("SELECT * FROM users WHERE username = :username LIMIT 1")
    with infra.db.engine.begin() as conn:
        res = conn.execute(query, values)

    row = res.fetchone()
    if row is None:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
        )

    if not lib.authenticate.verify_password(user.password, row[2]):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
        )
    #    print("user is ", user)
    access_token = jwt.create_access_token(payload={"username": user.username})
    return {"access_token": access_token}


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


@app.get("/v1/competitions")
def get_competitions(skip: int = 0, limit: int = None, db: Session = Depends(infra.db.get_db)):
    competitions = db.query(infra.db.Competitions).offset(skip).all()
    if limit is not None:
        competitions = competitions[:limit]
    return competitions


@app.get("/v1/competitions/{name}")
def search_competition(name: str, db: Session = Depends(infra.db.get_db)):
    competition = db.query(infra.db.Competitions).filter(infra.db.Competitions.title == name).first()
    if not competition:
        raise HTTPException(status_code=404, detail="Competition not found")
    return competition

@app.post("/v1/competitions")
def create_competition(title: str = Form(...),
                       hostUserId: str = Form(...),
                       description: str = Form(...),
                       queryType: str = Form(...),
                       schemaFile: UploadFile = File(...),
                       solution: UploadFile = File(...), db: Session = Depends(infra.db.get_db)):
    cur_time = datetime.now()
    dt_string = cur_time.strftime("%d/%m/%Y %H:%M:%S")

    schema_file = schemaFile.file.read()
    schema_file_contents = schema_file.decode("utf-8")

    solution_file = solution.file.read()
    solution_file_contents = solution_file.decode("utf-8")

    current_comp_id = len(db.query(infra.db.Competitions).all()) + 1
    dbname = "c" + str(current_comp_id)

    c_engine = create_engine("postgresql://testuser:testuser@localhost:5432/" + dbname, isolation_level="AUTOCOMMIT")
    if not database_exists(c_engine.url):
        create_database(c_engine.url)

    try:
        with c_engine.begin() as conn:
            query = text(schema_file_contents)
            conn.execute(query)

        schema_file_path = os.path.join(SCHEMA_PATH, dbname + ".sql")
        solution_file_path = os.path.join(ANS_PATH, dbname + ".sql")

        with open(schema_file_path, "w") as file:
            file.write(schema_file_contents)

        with open(solution_file_path, "w") as file:
            file.write(solution_file_contents)

        competition = infra.db.Competitions(c_id=current_comp_id, title=title, description=description,
                                            solution=solution_file_path,
                                            schema=schema_file_path,
                                            host_user_id=hostUserId,
                                            query_type=queryType,
                                            due_date=dt_string)
        db.add(competition)
        db.commit()
        db.refresh(competition)
        return {"c_id": "True"}

    except Exception as e:
        drop_database(c_engine.url)
        c_engine.dispose()
        raise HTTPException(status_code=404, detail="Competition Schema not valid")


@app.get("/v1/competitions/overview/{id}")
def get_competition_details(id: int, db: Session = Depends(infra.db.get_db)):
    competition = db.query(infra.db.Competitions).filter(infra.db.Competitions.c_id == id).first()
    if not competition:
        raise HTTPException(status_code=404, detail="Competition not found")

    competition_dict = {
        "title": competition.title,
        "description": competition.description,
        "host_user_id": competition.host_user_id,
    }

    return competition_dict


@app.get("/v1/competitions/leaderboard/{id}")
def get_leaderboard(id: int, db: Session = Depends(infra.db.get_db)):
    leaderboard = db.query(infra.db.Leaderboard).filter(infra.db.Leaderboard.c_id == id).all()
    if not leaderboard:
        raise HTTPException(status_code=404, detail="Leaderboard not found")
    return leaderboard


@app.get("/v1/competitions/leaderboard/{user_id}")
def get_leaderboard_user_details(user_id: int, db: Session = Depends(infra.db.get_db)):
    user_submissions = db.query(infra.db.Leaderboard).filter(infra.db.Leaderboard.user_id == user_id).all()
    if not user_submissions:
        raise HTTPException(status_code=404, detail="User Details not found")
    return user_submissions


@app.get("/v1/competitions/{id}/download")
def download_competition_schema(id: int, db: Session = Depends(infra.db.get_db)):
    try:
        with open(os.path.join(SCHEMA_PATH, str(id) + ".sql"), mode="r") as file:
            file_data = file.read()
            return StreamingResponse(iter(file_data), media_type="text/plain")

    except Exception as e:
        raise HTTPException(status_code=404, detail="Competition Details not found")
