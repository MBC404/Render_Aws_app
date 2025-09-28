# This is the final, corrected app/main.py file for your authentication service

import os
import secrets
import bcrypt
from fastapi import FastAPI, Form, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

# Import the database setup
from . import database

# --- Application Setup ---
app = FastAPI()
database.create_tables()
SESSION_STORE = {} # A simple in-memory store for user sessions

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# --- Helper Functions for Passwords ---
def verify_password(plain_password, hashed_password):
    # Check if the provided password matches the stored hash
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password):
    # Generate a secure hash for a new password
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# --- Dependencies ---
def get_db():
    # Dependency to get a database session for each request
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(request: Request, db: Session = Depends(get_db)):
    # Dependency to get the currently logged-in user from the session cookie
    session_id = request.cookies.get("session_id")
    if session_id and session_id in SESSION_STORE:
        username = SESSION_STORE[session_id]
        user = db.query(database.User).filter(database.User.username == username).first()
        return user
    return None

# --- Routes ---
@app.get("/")
def home(request: Request, user: database.User = Depends(get_current_user)):
    # If no user is logged in, redirect to the login page
    if not user:
        return RedirectResponse("/login", status_code=303)
    
    # This is the URL of your separate prediction service (e.g., on Hugging Face)
    # IMPORTANT: Replace this placeholder with your actual Hugging Face URL
    prediction_service_url = "https://YOUR-HUGGING-FACE-SPACE-URL" 
    
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "username": user.username,
        "prediction_url": prediction_service_url
    })

@app.get("/login")
def login_get(request: Request):
    # Display the login page, showing an error or success message if present
    return templates.TemplateResponse("login.html", {
        "request": request, 
        "error": request.query_params.get('error'), 
        "success": request.query_params.get('success')
    })

@app.post("/login")
async def login_post(request: Request, db: Session = Depends(get_db), username: str = Form(...), password: str = Form(...)):
    # Handle the login form submission
    user = db.query(database.User).filter(database.User.username == username).first()
    
    # Check if the user exists and the password is correct
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid username or password"})
    
    # Create a new session for the user
    session_id = secrets.token_hex(16)
    SESSION_STORE[session_id] = user.username
    
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(key="session_id", value=session_id, httponly=True)
    return response

@app.get("/signup")
def signup_get(request: Request):
    # Display the signup page
    return templates.TemplateResponse("signup.html", {"request": request, "error": request.query_params.get('error')})

@app.post("/signup")
async def signup_post(request: Request, db: Session = Depends(get_db), username: str = Form(...), password: str = Form(...), confirm_password: str = Form(...)):
    # Handle the signup form submission
    
    # 1. Check if the confirmed password matches
    if password != confirm_password:
        return templates.TemplateResponse("signup.html", {"request": request, "error": "Passwords do not match."})

    # 2. Check if the username is already taken
    db_user = db.query(database.User).filter(database.User.username == username).first()
    if db_user:
        return templates.TemplateResponse("signup.html", {"request": request, "error": "Username already exists."})
    
    # 3. Hash the password and create the new user in the database
    hashed_password = get_password_hash(password)
    new_user = database.User(username=username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Redirect to the login page with a success message
    return RedirectResponse("/login?success=Signup successful! Please login.", status_code=303)

@app.get("/logout")
def logout(request: Request):
    # Handle user logout by deleting the session
    session_id = request.cookies.get("session_id")
    if session_id in SESSION_STORE:
        del SESSION_STORE[session_id]
    
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("session_id")
    return response
