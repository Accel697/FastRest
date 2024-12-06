from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import Column, String, create_engine, BigInteger, MetaData, Table, text
from sqlalchemy.connectors import pyodbc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel

server = "DESKTOP-84G2R1V\\SQLEXPRESS"
database = "flower_service"

connectionString = f"mssql+pyodbc://@{server}/{database}?driver=ODBC+Driver+17+for+SQL+Server&Trusted_Connection=yes"

engine = create_engine(connectionString)
sessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
base = declarative_base()

try:
    with engine.connect() as connection:
        print("Успешное подключение к базе данных!")
        metadata = MetaData()
        userTable = Table("User", metadata, autoload_with=engine)
        print(f"Таблица найдена: {userTable}")
        base.metadata.create_all(engine)

except pyodbc.Error as ex:
    sqlstate = ex.args[0]
    if sqlstate == '28000':
        print("Ошибка аутентификации. Убедитесь, что SQL Server настроен на проверку подлинности Windows.")
    else:
        print("Ошибка при подключении:", ex)
except Exception as e:
    print("Другая ошибка при подключении:", e)


class User(base):
    __tablename__ = 'User'

    idUser = Column(BigInteger, primary_key=True, index=True)
    Login = Column(String, unique=True, nullable=False)
    Password = Column(String, nullable=False)


app = FastAPI(
    title="FastAPI",
    description="pracApi",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

class UserCreate(BaseModel):
    Login: str
    Password: str

class UserResponse(BaseModel):
    idUser: int
    Login: str

    class Config:
        orm_mode = True

def getDb():
    db = sessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/users", response_model=UserResponse, status_code=201)
def createUser(user: UserCreate, db: Session = Depends(getDb)):
    try:
        dbUser = User(Login=user.Login, Password=user.Password)
        db.add(dbUser)
        db.commit()
        db.refresh(dbUser)
        return dbUser
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Ошибка создания пользователя: {e}")


@app.get("/users", response_model=list[UserResponse])
def getUsers(db: Session = Depends(getDb)):
    users = db.query(User).all()
    return users


@app.get("/users/{userId}", response_model=UserResponse)
def getUser(userId: int, db: Session = Depends(getDb)):
    user = db.query(User).filter(User.idUser == userId).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user


@app.put("/users/{userId}", response_model=UserResponse)
def updateUser(userId: int, user: UserCreate, db: Session = Depends(getDb)):
    dbUser = db.query(User).filter(User.idUser == userId).first()
    if not dbUser:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    dbUser.Login = user.Login
    dbUser.Password = user.Password
    db.commit()
    return dbUser


@app.delete("/users/{userId}")
def deleteUser(userId: int, db: Session = Depends(getDb)):
    dbUser = db.query(User).filter(User.idUser == userId).first()
    if not dbUser:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    db.delete(dbUser)
    db.commit()
    return {"message": "Пользователь успешно удален"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)