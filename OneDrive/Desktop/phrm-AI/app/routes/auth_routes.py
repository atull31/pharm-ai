from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm 
from app.models import UserCreate, Token 
from app.auth import hash_password, verify_password, create_access_token
from app.db import db
from bson import ObjectId

router = APIRouter()

@router.post("/signup")
async def signup(user: UserCreate):
    existing_user = await db.users.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_pw = hash_password(user.password)
    user_dict = {"email": user.email, "hashed_password": hashed_pw} # Corrected 'hashed_pasword' typo if it exists
    result = await db.users.insert_one(user_dict)
    return {"message": "User created", "user_id": str(result.inserted_id)}

@router.post("/login", response_model=Token) # Ensure you return your Token model
async def login(form_data: OAuth2PasswordRequestForm = Depends()): # <--- THIS IS THE KEY CHANGE
    # Note: OAuth2PasswordRequestForm provides 'username' and 'password'.
    # Since your users are stored by 'email' in the DB (from signup),
    # we'll use form_data.username as the email for lookup.
    db_user = await db.users.find_one({"email": form_data.username}) # <--- Use form_data.username as email
    
    if not db_user or not verify_password(form_data.password, db_user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, # Use 401 for invalid credentials in login
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}, # Required for OAuth2
        )
    
    # If using ObjectId for user ID, ensure you convert to string if passing to JWT sub claim
    user_id_str = str(db_user["_id"]) if isinstance(db_user["_id"], ObjectId) else db_user["_id"]

    token = create_access_token({"sub": user_id_str, "email": db_user["email"]})
    return {"access_token": token, "token_type": "bearer"}