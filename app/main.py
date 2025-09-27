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

def get_current_user(request: Request, db: Session = Depends(get_db)):
    session_id = request.cookies.get("session_id")
    if session_id and session_id in SESSION_STORE:
        username = SESSION_STORE[session_id]
        user = db.query(database.User).filter(database.User.username == username).first()
        return user
    return None

# --- Routes ---
@app.get("/")
def home(request: Request, user: database.User = Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse("index.html", {"request": request, "username": user.username})

@app.post("/predict")
async def predict(file: UploadFile = File(...), user: database.User = Depends(get_current_user)):
    if not user:
        return Response("Unauthorized", status_code=401)

    contents = await file.read()
    pil_image = Image.open(io.BytesIO(contents))
    
    results = model.predict(pil_image)
    result = results[0]
    
    output_image_np = result.plot()
    output_image_bgr = cv2.cvtColor(output_image_np, cv2.COLOR_RGB2BGR)

    _, buffer = cv2.imencode(".jpg", output_image_bgr)
    
    return Response(content=buffer.tobytes(), media_type="image/jpeg")

@app.get("/login")
def login_get(request: Request):
    success_message = request.query_params.get('success')
    return templates.TemplateResponse("login.html", {"request": request, "success": success_message, "error": request.query_params.get('error')})

@app.post("/login")
async def login_post(request: Request, db: Session = Depends(get_db), username: str = Form(...), password: str = Form(...)):
    user = db.query(database.User).filter(database.User.username == username).first()
    if not user or not pwd_context.verify(password, user.hashed_password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid username or password"})
    
    session_id = secrets.token_hex(16)
    SESSION_STORE[session_id] = user.username
    
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
    
    # FIX: Truncate password to 72 bytes before hashing for bcrypt compatibility
    hashed_password = pwd_context.hash(password[:72])
    new_user = database.User(username=username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return RedirectResponse("/login?success=Signup successful! Please login.", status_code=303)

@app.get("/logout")
def logout(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id in SESSION_STORE:
        del SESSION_STORE[session_id]
    
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("session_id")
    return response