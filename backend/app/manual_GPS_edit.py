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
engine_sqlite = create_engine('sqlite:///E:\\Documents\\Coding\\myProjects\\golfmapper3\\backend\\app\\golf_mapper.db', echo=True)

Base = declarative_base()

class courses(Base):
    __tablename__ = 'courses'
    id = Column(Integer, primary_key=True)
    club_name = Column(String)
    course_name = Column(String)
    created_at = Column(String, nullable=True)
    address = Column(String, nullable=True)
    city = Column(String)
    state = Column(String)
    country = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)

    @property
    def display_name(self):
        """Returns formatted course name"""
        if self.club_name and self.course_name and self.club_name != self.course_name:
            return f"{self.club_name} - {self.course_name}"
        elif self.course_name:
            return self.course_name
        elif self.club_name:
            return self.club_name
        return ""

# Session = sessionmaker(bind=engine)
# session = Session()
Session_sqlite = sessionmaker(bind=engine_sqlite)
session_sqlite = Session_sqlite()

result = int(input(f"Which course id to you want to edit? "))
i = session_sqlite.get(courses, result)
# j = session.get(courses, result)

print(f'Course: {i.display_name}, city: {i.city}, country: {i.country}, id: {i.id}')
result = input("Is this the course you want to edit? ")
if result == 'y':
    new_lat = float(input('Enter Latitude: '))
    new_long = float(input('Enter Longitude: '))
    confirm = input(f'Do you want to update Course: {i.display_name}, city: {i.city}, country: {i.country}, id: {i.id}, with lat: {new_lat}, long={new_long} ? ')
    if confirm == 'y':
        i.latitude = new_lat
        i.longitude = new_long
        session_sqlite.commit()

        #update postgres database
        # j.latitude = new_lat
        # j.longitude = new_long
        # session.commit()
else:
    pass
