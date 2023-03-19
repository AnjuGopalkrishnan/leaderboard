from fastapi import FastAPI, Request
 
from starlette.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
 
templates = Jinja2Templates(directory="templates")
 
app = FastAPI()
 
app.mount("/static",StaticFiles(directory="static",html=True),name="static")
 
@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})



@app.get("/login/login.html")
def home(request: Request):
    return templates.TemplateResponse("login/login.html", {"request": request})

@app.get("/login/register.html")
def home(request: Request):
    return templates.TemplateResponse("login/register.html", {"request": request})