from pydantic import BaseModel, Field


class User(BaseModel):
    password: str
    username: str


class Competitions(BaseModel):
    title: str
    description: str
    schema_file: str = Field(..., alias="schema")
    solution: str
    host_user_id: int


class Submission(BaseModel):
    c_id: int
    user_id: int
    submission: str
