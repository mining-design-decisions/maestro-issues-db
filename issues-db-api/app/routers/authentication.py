from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from pydantic import BaseModel
from jose import JWTError, jwt
from pymongo.errors import DuplicateKeyError
from app.dependencies import users_collection
from app.config import SECRET_KEY


ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 1440


class Token(BaseModel):
    access_token: str
    token_type: str


class User(BaseModel):
    username: str
    password: str


pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')
router = APIRouter(tags=['authentication'])


CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail='Incorrect username or password',
    headers={'WWW-Authenticate': 'Bearer'}
)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def existing_user(username: str) -> bool:
    user = users_collection.find_one(
        {'_id': username},
        ['_id']
    )
    return user is not None


def authenticate_user(username: str, password: str) -> str | None:
    user = users_collection.find_one({
        '_id': username,
    })
    if user is None:
        return None
    if not verify_password(password, user['hashed_password']):
        return None
    # Return username
    return user['_id']


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({'exp': expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def validate_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise CREDENTIALS_EXCEPTION
    username: str = payload.get('username')
    if username is None or not existing_user(username):
        raise CREDENTIALS_EXCEPTION
    return {'username': username}


@router.post('/token', response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    username = authenticate_user(form_data.username, form_data.password)
    if username is None:
        raise CREDENTIALS_EXCEPTION
    access_token = create_access_token(data={'username': username})
    return {'access_token': access_token, 'token_type': 'bearer'}


@router.post('/create-account')
def create_account(new_account: User, token=Depends(validate_token)):
    try:
        users_collection.insert_one({
            '_id': new_account.username,
            'hashed_password': get_password_hash(new_account.password)
        })
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Username already exists'
        )
