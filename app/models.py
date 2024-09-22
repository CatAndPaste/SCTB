from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, ForeignKey, Float, Integer
from sqlalchemy.orm import declarative_base, relationship
import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String)
    language = Column(String)
    subscription = Column(Boolean, default=False)
    subscription_expires = Column(DateTime, default=None)
    api_key = Column(String)
    # Связь с параметрами и ордерами
    parameters = relationship("UserParameters", uselist=False, back_populates="user")
    orders = relationship("Order", back_populates="user")
    balance = relationship("Balance", uselist=False, back_populates="user")

class UserParameters(Base):
    __tablename__ = 'user_parameters'

    user_id = Column(BigInteger, ForeignKey('users.id'), primary_key=True)
    purchase_amount = Column(Float, default=1000.0)
    profit_percentage = Column(Float, default=5.0)
    purchase_delay = Column(Integer, default=10)
    growth_percentage = Column(Float, default=2.0)
    fall_percentage = Column(Float, default=3.0)
    autobuy_on_growth = Column(Boolean, default=False)
    autobuy_on_fall = Column(Boolean, default=False)

    user = relationship("User", back_populates="parameters")

class Order(Base):
    __tablename__ = 'orders'

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.id'))
    order_type = Column(String)  # 'buy' or 'sell'
    amount = Column(Float)
    price = Column(Float)
    status = Column(String, default='Open')  # 'Open' or 'Completed'
    date_created = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="orders")

class Admin(Base):
    __tablename__ = 'admins'

    id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String)
    password_hash = Column(String)

class SubscriptionOrder(Base):
    __tablename__ = 'subscription_orders'

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey('users.id'))
    order_id = Column(String)
    closed = Column(Boolean, default=False)
    description = Column(String)

class Balance(Base):
    __tablename__ = 'balances'

    user_id = Column(BigInteger, ForeignKey('users.id'), primary_key=True)
    btc_available = Column(Float, default=0.0)
    btc_frozen = Column(Float, default=0.0)
    usdt_available = Column(Float, default=10000.0)  # Начальный баланс для тестирования
    usdt_frozen = Column(Float, default=0.0)

    user = relationship("User", back_populates="balance")
