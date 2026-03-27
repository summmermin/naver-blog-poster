from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from config import DB_PATH

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class PostQueue(Base):
    __tablename__ = "post_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100), default="")
    tags = Column(String(500), default="")  # comma separated
    image_paths = Column(Text, default="")  # comma separated file paths
    is_published = Column(Boolean, default=False)
    scheduled_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    published_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)


Base.metadata.create_all(engine)
