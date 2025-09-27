import io
import os
import secrets
import cv2
import numpy as np
from fastapi import FastAPI, File, Form, Request, UploadFile, Depends
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image
from ultralytics import YOLO
from sqlalchemy.orm import Session
from passlib.context import CryptContext

# Import the new database setup
from . import database

# --- Application Setup ---
app = FastAPI()

# Create the 'users' table in the database if it doesn't exist
# This will be run once when the application starts
database.create_tables()

# --- Password Hashing Setup ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- In-Memory Session Storage ---
SESSION_STORE = {}

# --- Path and Model Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(BASE_DIR)
model_path = os.path.join(project_root, "best.pt")
model = YOLO(model_path)
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")


# --- Dependencies ---
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id in SESSION_STORE:
        return SESSION_STORE[session_id].get("username")
    return None

# --- Routes ---
@app.get("/")
def home(request: Request, username: str = Depends(get_current_user)):
    if username:
        return templates.TemplateResponse("index.html", {"request": request, "username": username})
    return RedirectResponse("/login", status_code=303)

@app.post("/predict")
async def predict(file: UploadFile = File(...), username: str = Depends(get_current_user)):
    if not username:
        return RedirectResponse("/login", status_code=303)
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    results = model(img)
    annotated_img_array = results[0].plot()
    annotated_img_rgb = cv2.cvtColor(annotated_img_array, cv2.COLOR_BGR2RGB)
    im = Image.fromarray(annotated_img_rgb)
    with io.BytesIO() as buf:
        im.save(buf, format='JPEG')
        image_bytes = buf.getvalue()
    return Response(content=image_bytes, media_type="image/jpeg")

@app.get("/login")
def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": request.query_params.get('error'), "success": request.query_params.get('success')})

@app.post("/login")
async def login_post(request: Request, db: Session = Depends(get_db), username: str = Form(...), password: str = Form(...)):
    user = db.query(database.User).filter(database.User.username == username).first()
    if not user or not pwd_context.verify(password, user.hashed_password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid username or password"})

    session_id = secrets.token_hex(16)
    SESSION_STORE[session_id] = {"username": username}
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(key="session_id", value=session_id, httponly=True)
    return response

@app.get("/signup")
def signup_get(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request, "error": request.query_params.get('error')})

@app.post("/signup")
async def signup_post(request: Request, db: Session = Depends(get_db), username: str = Form(...), password: str = Form(...), confirm_password: str = Form(...)):
    if password != confirm_password:
        return templates.TemplateResponse("signup.html", {"request": request, "error": "Passwords do not match"})
    
    db_user = db.query(database.User).filter(database.User.username == username).first()
    if db_user:
        return templates.TemplateResponse("signup.html", {"request": request, "error": "User already exists. Please login."})
    
    hashed_password = pwd_context.hash(password)
    new_user = database.User(username=username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return RedirectResponse("/login?success=Signup successful! Please login.", status_code=303)

@app.get("/logout")
def logout(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id and session_id in SESSION_STORE:
        del SESSION_STORE[session_id]
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(key="session_id")
    return response