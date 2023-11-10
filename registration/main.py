from fastapi import FastAPI, status, Depends, HTTPException
from . import models
from .database import engine, SessionLocal
from .schemas import User
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from motor.motor_asyncio import AsyncIOMotorClient

models.Base.metadata.create_all(bind=engine)

MONGODB_URL = "mongodb://localhost:27017"
mongo_client = AsyncIOMotorClient(MONGODB_URL)
mongo_db = mongo_client["profile_pictures"]

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
async def register(request: User, db: Session = Depends(get_db)):
    if check_email_exist(request.email, db):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exist")
    
    hashed_password = pwd_context.hash(request.password)

    user = models.User(first_name=request.first_name, last_name=request.last_name, password=hashed_password, email=request.email, phone=request.phone)
    db.add(user)
    db.commit()
    db.refresh(user)

    profile_picture = await request.profile_picture.read()
    await mongo_db.profile_pictures.insert_one({"user_id": user.id, "profile_picture": profile_picture})

    return {"message": "User registered successfully"}


@app.get("/user/{id}/", response_model=User)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    profile_picture = await mongo_db.profile_pictures.find_one({"user_id": user_id})
    return {"full_name": db_user.full_name, "email": db_user.email, "phone": db_user.phone}