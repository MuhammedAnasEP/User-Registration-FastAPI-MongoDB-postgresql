from pydantic import BaseModel
from fastapi import UploadFile, File

class User(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: str
    password: str
    profile_picture: UploadFile = File(...)