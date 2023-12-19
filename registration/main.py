from fastapi import FastAPI, status, Depends, HTTPException, UploadFile, File
from . import models
from .database import engine, SessionLocal
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from motor.motor_asyncio import AsyncIOMotorClient
import os
# from pymongo import MongoClient

models.Base.metadata.create_all(bind=engine)

MONGODB_URL = "mongodb://localhost:27017"
mongo_client = AsyncIOMotorClient(MONGODB_URL)
mongo_db = mongo_client["profile_pictures"]


# client = MongoClient("mongodb://localhost:27017/")
# database = client["profile_picture"]
# users_collection = database["users"]

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_email_exist(email, db):
    user = db.query(models.User).filter(models.User.email == email)
    if not user.first():
        return False
    return True

@app.post('/register',status_code=status.HTTP_201_CREATED)
async def register(first_name: str,
    last_name: str,
    email: str,
    phone: str,
    password: str,profile_picture: UploadFile = File(None), db: Session = Depends(get_db)):
    if check_email_exist(email, db):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exist")
    
    hashed_password = pwd_context.hash(password)

    user = models.User(first_name=first_name, last_name=last_name, password=hashed_password, email=email, phone=phone)
    db.add(user)
    db.commit()
    db.refresh(user)

    if profile_picture:
        profile_picture_path = f"uploads/{user.id}_{profile_picture.filename}"
        os.makedirs(os.path.dirname(profile_picture_path), exist_ok=True)
        with open(profile_picture_path, "wb") as f:
            f.write(profile_picture.file.read())


        await mongo_db.profile_pictures.insert_one({"user_id": user.id, "profile_picture": profile_picture})

    return {"message": "User registered successfully"}


@app.get("/user/{id}/")
async def get_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    profile_picture = await mongo_db.profile_pictures.find_one({"user_id": user_id})
    return {"full_name": db_user.full_name, "email": db_user.email, "phone": db_user.phone}
