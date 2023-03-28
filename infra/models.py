from fastapi import UploadFile, File, Form
from pydantic import BaseModel, Field


class User(BaseModel):
    password: str
    username: str


class FormSchema(BaseModel):
    title: str = Form(...)
    hostUserId: str = Form(...)
    description: str = Form(...)
    queryType: str = Form(...)
    schemaFile: UploadFile = File(...)
    solution: UploadFile = File(...)


class Submission(BaseModel):
    c_id: int
    user_id: int
    submission: str
