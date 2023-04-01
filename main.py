import os.path
from datetime import datetime
import re

from fastapi import FastAPI, HTTPException, Depends, Form, UploadFile, File, Header
from fastapi.responses import StreamingResponse
from fastapi import Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text, create_engine, desc, and_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy_utils import database_exists, create_database, drop_database
from starlette.templating import Jinja2Templates
import typing
from fastapi.responses import StreamingResponse
import io
from sqlalchemy import select, desc, asc, func

import infra.db
import lib.authenticate
from infra import models
from infra.db import User
from lib import jwt_methods, metricCal

templates = Jinja2Templates(directory="templates")

SCHEMA_PATH = "schemas"
ANS_PATH = "answers"
CONTESTANT_SOLUTIONS = "solutions"

if not os.path.exists(SCHEMA_PATH):
    os.mkdir(SCHEMA_PATH)

if not os.path.exists(ANS_PATH):
    os.mkdir(ANS_PATH)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static", html=True), name="static")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/user/login")


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


@app.get("/leaderboard.html")
def home(request: Request):
    return templates.TemplateResponse("leaderboard.html", {"request": request})


@app.get("/hostcompetition.html")
def home(request: Request):
    return templates.TemplateResponse("hostcompetition.html", {"request": request})


@app.post("/v1/user/register")
def register(user: models.User, db: Session = Depends(infra.db.get_db)):
    hashPwd = lib.authenticate.get_password_hash(user.password)

    new_user = User(username=user.username, password=hashPwd, email=user.email)
    db.add(new_user)
    try:
        db.commit()
        return {
            "username": user.username,
            "register_success": True
        }
    except SQLAlchemyError as e:
        return {
            "register_success": False
        }


@app.post("/v1/user/login")
def login(user: models.UserLogin):
    values = {
        'email': user.username,
    }
    query = text("SELECT * FROM users WHERE email = :email LIMIT 1")
    with infra.db.engine.begin() as conn:
        res = conn.execute(query, values)

    row = res.fetchone()
    if row is None:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
        )

    if not lib.authenticate.verify_password(user.password, row[-1]):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
        )
    #    print("user is ", user)
    access_token = jwt_methods.create_access_token(payload={"username": user.username})
    print(access_token)
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/v1/user/{id}/hosted")
def hosted(id, current_user: infra.db.User = Depends(jwt_methods.get_current_user)):
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
def getcompetitions(id, current_user: infra.db.User = Depends(jwt_methods.get_current_user)):
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
def get_competitions(skip: int = 0, limit: int = None, db: Session = Depends(infra.db.get_db),
                     current_user: infra.db.User = Depends(jwt_methods.get_current_user)):
    competitions = db.query(infra.db.Competitions).offset(skip).all()
    if limit is not None:
        competitions = competitions[:limit]
    return competitions


@app.get("/v1/competitions/{name}")
def search_competition(name: str, db: Session = Depends(infra.db.get_db),
                       current_user: infra.db.User = Depends(jwt_methods.get_current_user)):
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
                       solution: UploadFile = File(...),
                       db: Session = Depends(infra.db.get_db),
                       current_user: infra.db.User = Depends(jwt_methods.get_current_user)):
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
def get_competition_details(id: int, db: Session = Depends(infra.db.get_db),
                            current_user: infra.db.User = Depends(jwt_methods.get_current_user)):
    competition = db.query(infra.db.Competitions).filter(infra.db.Competitions.c_id == id).first()
    if not competition:
        raise HTTPException(status_code=404, detail="Competition not found")

    competition_dict = {
        "title": competition.title,
        "description": competition.description,
        "host_user_id": competition.host_user_id,
    }

    return competition_dict


@app.get("/v1/competitions/leaderboard/{competition_id}/{user_id}")
def get_leaderboard_user_details(user_id: int, competition_id: int, db: Session = Depends(infra.db.get_db)):
    user_submissions = db.query(infra.db.Submissions).filter(
        infra.db.Submissions.user_id == user_id and infra.db.Submissions.c_id == competition_id).all()
    if not user_submissions:
        raise HTTPException(status_code=404, detail="User Details not found")
    return user_submissions


@app.get("/v1/competitions/{id}/download")
def download_competition_schema(id: int, db: Session = Depends(infra.db.get_db),
                                current_user: infra.db.User = Depends(jwt_methods.get_current_user)):
    try:
        with open(os.path.join(SCHEMA_PATH, "c" + str(id) + ".sql"), mode="r") as file:
            file_data = file.read()
            file_like = io.StringIO(file_data)
            return StreamingResponse(iter(lambda: file_like.read(1024), ''), media_type="text/plain")

    except Exception as e:
        raise HTTPException(status_code=404, detail="Competition Details not found")


@app.post("/v1/evaluations/competition/{c_id}/submissions/")
def evaluate_submission(c_id: int, db: Session = Depends(infra.db.get_db),
                        solution: UploadFile = File(...),
                        current_user: infra.db.User = Depends(jwt_methods.get_current_user)):

    user_id = current_user.user_id
    number_submissions = db.query(infra.db.Submissions).filter(infra.db.Submissions.c_id == c_id).filter(
        infra.db.Submissions.user_id == user_id).count()

    solution_file = solution.read()
    file_name_submission = str(c_id) + "_" + str(user_id) + "_" + str(number_submissions + 1) + ".sql"

    solution_file_path = os.path.join(CONTESTANT_SOLUTIONS, file_name_submission)
    with open(solution_file_path, "w") as file:
        file.write(solution_file.decode("utf-8"))

    submission_file_path_row = db.query(infra.db.Submissions.submission).filter(
        infra.db.Submissions.c_id == c_id and infra.db.Submissions.user_id == user_id).order_by(
        desc(infra.db.Submissions.timestamp)).first()

    for row in submission_file_path_row:
        submission_file_path = row

    dbname = "c" + str(c_id)

    c_engine = create_engine('postgresql://postgres:admin@localhost:5432/' + dbname, echo=True)

    connection = c_engine.connect()
    with c_engine.begin() as conn:
        with open(solution_file_path) as file:
            query = text(file.read())
            expected_result = conn.execute(query).all()

        sum_plan_times = 0
        sum_exec_times = 0
        with open(submission_file_path) as file:
            query = text(file.read())
            user_result = conn.execute(query).all()

            # Take avg of 5 execution performance
            for _ in range(5):
                analyze_result_u = conn.execute(text(f'EXPLAIN ANALYZE {query}'))
                for row in analyze_result_u:
                    if ("Planning Time") in str(row):
                        user_plan_time = float(re.findall(r'[\d]*[.][\d]+', str(row))[0])
                        sum_plan_times = sum_plan_times + user_plan_time

                    if ("Execution Time") in str(row):
                        user_exec_time = float(re.findall(r'[\d]*[.][\d]+', str(row))[0])
                        sum_exec_times = sum_exec_times + user_exec_time

        user_plan_time = sum_plan_times / 5
        user_exec_time = sum_exec_times / 5
        conn.close()

    connection.close()

    score = 0
    # Compare results
    if (user_result == expected_result):
        score = score + 1

    # Further checks only if results match
    if (score == 1):
        max_time = 10
        pt = max_time - user_plan_time
        et = max_time - user_exec_time
        tt = max_time - (user_plan_time + user_exec_time)
        score = score + pt + et + tt

    # update submission tables

    x = db.query(infra.db.Submissions). \
        filter(infra.db.Submissions.c_id == c_id,
               infra.db.Submissions.user_id == user_id). \
        order_by(desc(infra.db.Submissions.timestamp)). \
        first()

    if x:
        x.score = score
        db.commit()

    # TODO changes for slowest - query_type

    return {"query_score": score}


@app.get("/v1/competitions/leaderboard/{competition_id}")
def get_leaderboard(competition_id: int, db: Session = Depends(infra.db.get_db)):
    competition = db.query(infra.db.competitions.c.query_type).filter(
        infra.db.competitions.c.c_id == competition_id).first()

    if competition is None:
        return {"error": "Competition not found"}

    query_type = competition[0]

    if query_type == 0:
        subquery = (
            select([func.max(infra.db.submissions.c.total_time).label("best_time"), infra.db.submissions.c.user_id])
            .where(infra.db.submissions.c.c_id == competition_id)
            .group_by(infra.db.submissions.c.user_id)
            .alias("best_submissions")
        )

        query = (
            select([infra.db.submissions])
            .select_from(infra.db.submissions.join(subquery, and_(
                infra.db.submissions.c.user_id == subquery.c.user_id,
                infra.db.submissions.c.total_time == subquery.c.best_time
            )))
            .where(infra.db.submissions.c.c_id == competition_id)
            .order_by(asc(infra.db.submissions.c.total_time))
        )
    elif query_type == 1:
        subquery = (
            select([func.min(infra.db.submissions.c.total_time).label("best_time"), infra.db.submissions.c.user_id])
            .where(infra.db.submissions.c.c_id == competition_id)
            .group_by(infra.db.submissions.c.user_id)
            .alias("best_submissions")
        )

        query = (
            select([infra.db.submissions])
            .select_from(infra.db.submissions.join(subquery, and_(
                infra.db.submissions.c.user_id == subquery.c.user_id,
                infra.db.submissions.c.total_time == subquery.c.best_time
            )))
            .where(infra.db.submissions.c.c_id == competition_id)
            .order_by(desc(infra.db.submissions.c.total_time))
        )
    else:
        return {"error": "Invalid query type"}

    submissions = db.execute(query).fetchall()

    if not submissions:
        raise HTTPException(status_code=404, detail="User Details not found")

    return submissions


@app.get("/v1/competitions/{id}/download")
def download_competition_schema(id: int, db: Session = Depends(infra.db.get_db),
                                current_user: infra.db.User = Depends(jwt_methods.get_current_user)):
    pass


@app.get("/v1/queryMetrics")
def test(current_user: infra.db.User = Depends(jwt_methods.get_current_user)):
    query = "select * from users"
    print(current_user)
    return lib.metricCal.get_query_score(query)