import os
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Fetch environment variables
DB_USER = os.getenv('DB_USER', 'default_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'default_password')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')

# use with postgres
# SQLALCHEMY_DATABASE_URL = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/golfmapper2?options=-csearch_path%3Dmain'
# engine = create_engine(SQLALCHEMY_DATABASE_URL)

# old sqlite connection
# engine_sqlite = create_engine('sqlite:////Users/george/Code/keys/golfMapperDB/garmin.db', echo=True)
engine_sqlite = create_engine('sqlite:///E:\\Documents\\Coding\\myProjects\\golfmapper3\\backend\\app\\garmin.db', echo=True)

Base = declarative_base()

class courses(Base):
    __tablename__ = 'courses'
    id = Column(Integer, primary_key=True)
    g_course = Column(String(250))
    g_address = Column(String(250))
    g_city = Column(String(100))
    g_state = Column(String(40))
    g_country = Column(String(40))
    g_latitude = Column(Float)
    g_longitude = Column(Float)

# Session = sessionmaker(bind=engine)
# session = Session()
Session_sqlite = sessionmaker(bind=engine_sqlite)
session_sqlite = Session_sqlite()

result = int(input(f"Which course id to you want to edit? "))
i = session_sqlite.get(courses, result)
# j = session.get(courses, result)

print(f'Course: {i.g_course}, city: {i.g_city}, country: {i.g_country}, id: {i.id}')
result = input("Is this the course you want to edit? ")
if result == 'y':
    new_lat = float(input('Enter Latitude: '))
    new_long = float(input('Enter Longitude: '))
    confirm = input(f'Do you want to update Course: {i.g_course}, city: {i.g_city}, country: {i.g_country}, id: {i.id}, with lat: {new_lat}, long={new_long} ? ')
    if confirm == 'y':
        i.g_latitude = new_lat
        i.g_longitude = new_long
        session_sqlite.commit()

        #update postgres database
        # j.g_latitude = new_lat
        # j.g_longitude = new_long
        # session.commit()
else:
    pass
