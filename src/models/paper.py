import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from src.db.interfaces.postgresql import Base


class Paper(Base):
    __tablename__ = "papers"

    # Core arXiv metadata
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    arxiv_id = Column(String, unique=True, nullable=False, index=True)
    title = Column(String, nullable=False)
    authors = Column(JSON, nullable=False)
    abstract = Column(Text, nullable=False)
    categories = Column(JSON, nullable=False)
    published_date = Column(DateTime, nullable=False)
    pdf_url = Column(String, nullable=False)

