from sqlalchemy import Column, Integer, String
from sqlalchemy import UniqueConstraint
from database import Base

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True)
    client_name = Column(String)
    client_phone = Column(String)
    service = Column(String)
    barber = Column(String)
    date = Column(String)
    time = Column(String)
    duration = Column(Integer)

    __table_args__ = (
        UniqueConstraint('date', 'time', 'barber', name='unique_booking'),
    )