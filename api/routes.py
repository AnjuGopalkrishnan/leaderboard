from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

# Set up database connection
SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Initialize the FastAPI application
app = FastAPI()


# Define the SQLAlchemy Base
Base = declarative_base()


# Define the database models
class User(Base):
    __tablename__ = "user"
    user_id = Column(Integer, primary_key=True, index=True)
    password = Column(String)
    user_name = Column(String)


class Competition(Base):
    __tablename__ = "competition"
    c_id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(String)
    solution = Column(String)
    host_user_id = Column(Integer, ForeignKey("users.user_id"))
    due_date = Column(DateTime)
    host_user = relationship("User", back_populates="competition")


class Submission(Base):
    __tablename__ = "submission"
    c_id = Column(Integer, ForeignKey("competitions.c_id"), primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    submission = Column(String)
    score = Column(Integer)
    competition = relationship("Competition", back_populates="submission")
    user = relationship("User", back_populates="submission")


class Leaderboard(Base):
    __tablename__ = "leaderboard"

    c_id = Column(Integer, ForeignKey("competitions.c_id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True)
    score = Column(Float, nullable=False)

    competition = relationship("Competition", back_populates="leaderboard")
    user = relationship("User", back_populates="leaderboard")
    
User.competitions = relationship("Competition", back_populates="host_user")
Competition.submissions = relationship("Submission", back_populates="competition")
User.submissions = relationship("Submission", back_populates="user")


# Define helper functions
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/v1/competitions")
def get_competitions(skip: int = 0, limit: int = None, db: Session = Depends(get_db)):
    competitions = db.query(Competition).offset(skip).all()
    if limit is not None:
        competitions = competitions[:limit]
    return competitions


@app.get("/v1/competitions/{name}")
def search_competition(name: str, db: Session = Depends(get_db)):
    competition = db.query(Competition).filter(Competition.title == name).first()
    if not competition:
        raise HTTPException(status_code=404, detail="Competition not found")
    return competition


@app.post("/v1/competitions")
def create_competition(title: str, description: str, schema_file: str, solution_file: str, due_date: str, host_user_id: int, db: Session = Depends(get_db)):
    due_date = datetime.strptime(due_date, "%Y-%m-%d %H:%M:%S")
    competition = Competition(title=title, description=description, solution=solution_file, host_user_id=host_user_id, due_date=due_date)
    db.add(competition)
    db.commit()
    db.refresh(competition)
    return {"c_id": competition.c_id}


@app.get("/v1/competitions/overview/{id}")
def get_competition_details(id: int, db: Session = Depends(get_db)):
    competition = db.query(Competition).filter(Competition.c_id == id).first()
    if not competition:
        raise HTTPException(status_code=404, detail="Competition not found")
        
    competition_dict = {
        "title": competition.title,
        "description": competition.description,
    }
    
    return competition_dict

@app.get("/v1/competitions/leaderboard/{id}")
def get_leaderboard(id: int, db: Session = Depends(get_db)):
    leaderboard = db.query(Leaderboard).filter(Leaderboard.c_id == id).all()
    if not leaderboard:
        raise HTTPException(status_code=404, detail="Leaderboard not found")
    return leaderboard

@app.get("/v1/competitions/leaderboard/{user_id}")
def get_leaderboard_user_details(user_id: int, db: Session = Depends(get_db)):
    user_submissions = db.query(Leaderboard).filter(Leaderboard.user_id == user_id).all()
    if not user_submissions:
        raise HTTPException(status_code=404, detail="User Details not found")
    return user_submissions

@app.get("/v1/competitions/{id}/download")
def download_competition_schema(id: int, db: Session = Depends(get_db)):
    pass

@app.post("/v1/competitions/{id}/submissions")
def submit_solution(id: int, user_id: int, submission: str, db: Session = Depends(get_db)):
    competition = db.query(Competition).filter(Competition.c_id == id).first()
    if not competition:
        raise HTTPException(status_code=404, detail="Competition not found")
        
    submission = Submission(c_id=id, user_id=user_id, submission=submission)
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return {"submission_id": submission.c_id, "user_id": submission.user_id, "c_id": submission.c_id}
