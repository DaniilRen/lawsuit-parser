from sqlalchemy import Column, String, DateTime, JSON, Integer, Text, ForeignKey, Index, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class ParsingSession(Base):
    __tablename__ = 'parsing_sessions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    total_sources = Column(Integer)
    successful_sources = Column(Integer)
    status = Column(String(20), default='running')
    
    __table_args__ = (
        Index('idx_session_started', 'started_at'),
        Index('idx_session_status', 'status'),
    )


class Company(Base):
    __tablename__ = 'companies'
    
    inn = Column(String(12), primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_company_inn', 'inn'),
    )


class ParserData(Base):
    __tablename__ = 'parser_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    inn = Column(String(12), ForeignKey('companies.inn', ondelete='CASCADE'), nullable=False)
    source_name = Column(String(100), nullable=False)
    session_id = Column(Integer, ForeignKey('parsing_sessions.id', ondelete='CASCADE'), nullable=False)
    data = Column(JSON, nullable=False)
    parsed_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_parser_data_inn', 'inn'),
        Index('idx_parser_data_source', 'source_name'),
        Index('idx_parser_data_session', 'session_id'),
        Index('idx_parser_data_inn_source_session', 'inn', 'source_name', 'session_id'),
    )


class ParsingAttempt(Base):
    __tablename__ = 'parsing_attempts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    inn = Column(String(12), nullable=False)
    source_name = Column(String(100), nullable=False)
    session_id = Column(Integer, ForeignKey('parsing_sessions.id', ondelete='CASCADE'), nullable=False)
    status = Column(String(20), nullable=False)
    error_message = Column(Text)
    duration_ms = Column(Integer)
    attempted_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_attempt_inn', 'inn'),
        Index('idx_attempt_source', 'source_name'),
        Index('idx_attempt_session', 'session_id'),
        Index('idx_attempt_status', 'status'),
        Index('idx_attempt_inn_source_session', 'inn', 'source_name', 'session_id'),
    )


class SourceRegistry(Base):
    __tablename__ = 'source_registry'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_name = Column(String(100), nullable=False, unique=True)
    module_name = Column(String(100), nullable=False)
    class_name = Column(String(100), nullable=False)
    enabled = Column(String(5), default='true')
    config = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_source_registry_name', 'source_name'),
        Index('idx_source_registry_enabled', 'enabled'),
    )