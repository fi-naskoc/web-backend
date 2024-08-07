import datetime

from sqlalchemy import Column, Integer, String, Boolean, Enum, Text, text
from sqlalchemy.types import TIMESTAMP
from sqlalchemy.orm import relationship

from . import Base


class User(Base):
    __tablename__ = 'users'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8mb4'
    }

    id = Column(Integer, primary_key=True)
    email = Column(String(50), nullable=False, unique=True)
    github = Column(String(50), nullable=True)
    discord = Column(String(50), nullable=True)
    phone = Column(String(15))
    first_name = Column(String(50), nullable=False)
    nick_name = Column(String(50))
    last_name = Column(String(50), nullable=False)
    sex = Column(Enum('male', 'female', 'other'), nullable=False)
    password = Column(String(255), nullable=False)
    short_info = Column(Text, nullable=False)
    profile_picture = Column(String(255))
    role = Column(
        Enum('admin', 'org', 'participant', 'participant_hidden', 'tester'),
        nullable=False, default='participant', server_default='participant')
    enabled = Column(Boolean, nullable=False, default=True, server_default='1')
    registered = Column(TIMESTAMP, nullable=False,
                        default=datetime.datetime.utcnow,
                        server_default=text('CURRENT_TIMESTAMP'))
    last_logged_in = Column(TIMESTAMP, nullable=True)

    tasks = relationship("Task", primaryjoin='User.id == Task.author')
