import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Fetch environment variables
DB_USER = os.getenv('DB_USER', 'default_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'default_password')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
USE_SQLITE_DB = os.getenv('USE_SQLITE_DB', 'true')
SQLITE_DB_URL = os.getenv('SQLITE_DB_URL', None)


# use with mysql
# SQLALCHEMY_DATABASE_URL = 'mysql+pymysql://root:password@10.9.8.221:3306/garminApplicationDatabase'
# engine = create_engine(SQLALCHEMY_DATABASE_URL)

if USE_SQLITE_DB.lower() == 'true':
    if SQLITE_DB_URL:
        SQLALCHEMY_DATABASE_URL = f'sqlite:///{SQLITE_DB_URL}'
    else:
        SQLALCHEMY_DATABASE_URL = "sqlite:///./garmin.db"
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
else:
    SQLALCHEMY_DATABASE_URL = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/golfmapper2?options=-csearch_path%3Dmain'
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
