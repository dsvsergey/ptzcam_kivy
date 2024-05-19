import os
from sqlalchemy import create_engine, Integer, String, Text, Column, \
    ForeignKey, BLOB
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy_utils import database_exists, create_database


SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.expanduser('~/Documents/')}bzbcam.db"

Base = declarative_base()


class Camera(Base):
    __tablename__ = 'camera'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text)
    ip_address = Column(String(20), index=True)
    visca_port = Column(Integer)
    rtsp_port = Column(Integer)
    user_name = Column(Text)
    password = Column(Text)
    speed = Column(Integer)
    presets = relationship('Preset', backref='camera', lazy='dynamic')
    player_settings = Column(Text)
    sub_stream = Column(Text)
    main_stream = Column(Text)

    def get_description(self):
        return f'ip:{self.ip_address}; visca:{self.visca_port}; ' \
               f'rtsp: {self.rtsp_port}'


class Preset(Base):
    __tablename__ = 'preset'
    id = Column(Integer, primary_key=True, autoincrement=True)
    camera_id = Column(Integer, ForeignKey('camera.id'), nullable=False)
    name = Column(Text)
    number = Column(Integer)
    img = Column(BLOB)
    speed = Column(Integer)


class AppSettings(Base):
    __tablename__ = 'settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    main_window = Column(Text)


engine = create_engine(SQLALCHEMY_DATABASE_URI)
if not database_exists(engine.url):
    create_database(engine.url)
    table_objects = [Camera.__table__, Preset.__table__, AppSettings.__table__]
    Base.metadata.create_all(engine, tables=table_objects)
session = scoped_session(sessionmaker(bind=engine))
