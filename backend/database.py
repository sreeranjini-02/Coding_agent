from sqlalchemy import create_engine, URL
from sqlalchemy.orm import sessionmaker

# MySQL Credentials
MYSQL_USER = "root"
MYSQL_PASSWORD = "Sree@MySQL2026"

DATABASE_NAME = "coding_agent_db"

# Database Connection
DATABASE_URL = URL.create(
    drivername="mysql+pymysql",
    username=MYSQL_USER,
    password=MYSQL_PASSWORD,
    host="localhost",
    port=3306,
    database=DATABASE_NAME
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)