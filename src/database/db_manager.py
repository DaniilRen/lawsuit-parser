from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from src.database.models import Base, Company, ParserData, ParsingAttempt, ParsingSession, SourceRegistry


class DatabaseManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.engine = None
        self.SessionLocal = None
        self._connect()
    
    def _connect(self) -> None:
        db_config = self.config
        host = db_config.get('host', 'localhost')
        port = db_config.get('port', 5432)
        name = db_config.get('name', 'company_parser')
        user = db_config.get('user', 'postgres')
        password = db_config.get('password', 'postgres')
        
        database_url = f"postgresql://{user}:{password}@{host}:{port}/{name}"
        
        pool_size = db_config.get('pool_size', 10)
        max_overflow = db_config.get('max_overflow', 20)
        pool_timeout = db_config.get('pool_timeout', 30)
        pool_recycle = db_config.get('pool_recycle', 3600)
        echo = db_config.get('echo', False)
        
        self.engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            echo=echo,
            connect_args=db_config.get('connect_args', {})
        )
        
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def create_tables(self) -> None:
        Base.metadata.create_all(bind=self.engine)
    
    def drop_tables(self) -> None:
        Base.metadata.drop_all(bind=self.engine)
    
    def get_session(self) -> Session:
        return self.SessionLocal()
    
    def create_parsing_session(self) -> ParsingSession:
        session = self.get_session()
        try:
            parsing_session = ParsingSession()
            session.add(parsing_session)
            session.commit()
            session.refresh(parsing_session)
            return parsing_session
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def complete_parsing_session(self, session_id: int, total_sources: int, successful_sources: int) -> None:
        session = self.get_session()
        try:
            parsing_session = session.query(ParsingSession).filter(ParsingSession.id == session_id).first()
            if parsing_session:
                parsing_session.completed_at = datetime.utcnow()
                parsing_session.total_sources = total_sources
                parsing_session.successful_sources = successful_sources
                parsing_session.status = 'completed'
                session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_company(self, inn: str) -> Optional[Company]:
        session = self.get_session()
        try:
            return session.query(Company).filter(Company.inn == inn).first()
        finally:
            session.close()
    
    def get_or_create_company(self, inn: str) -> Company:
        session = self.get_session()
        try:
            company = session.query(Company).filter(Company.inn == inn).first()
            if not company:
                company = Company(inn=inn)
                session.add(company)
                session.commit()
                session.refresh(company)
            return company
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def save_parser_data(self, inn: str, source_name: str, session_id: int, data: Dict[str, Any]) -> ParserData:
        session = self.get_session()
        try:
            parser_data = ParserData(
                inn=inn,
                source_name=source_name,
                session_id=session_id,
                data=data
            )
            session.add(parser_data)
            session.commit()
            session.refresh(parser_data)
            return parser_data
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_parser_data(self, inn: str, source_name: str = None, session_id: int = None) -> List[ParserData]:
        session = self.get_session()
        try:
            query = session.query(ParserData).filter(ParserData.inn == inn)
            if source_name:
                query = query.filter(ParserData.source_name == source_name)
            if session_id:
                query = query.filter(ParserData.session_id == session_id)
            return query.order_by(ParserData.parsed_at.desc()).all()
        finally:
            session.close()
    
    def get_latest_parser_data(self, inn: str, source_name: str) -> Optional[ParserData]:
        session = self.get_session()
        try:
            return session.query(ParserData).filter(
                and_(ParserData.inn == inn, ParserData.source_name == source_name)
            ).order_by(ParserData.parsed_at.desc()).first()
        finally:
            session.close()
    
    def get_parser_data_by_session(self, session_id: int) -> List[ParserData]:
        session = self.get_session()
        try:
            return session.query(ParserData).filter(ParserData.session_id == session_id).all()
        finally:
            session.close()
    
    def add_parsing_attempt(self, inn: str, source_name: str, session_id: int, 
                           status: str, error_message: str = None, duration_ms: int = None) -> ParsingAttempt:
        session = self.get_session()
        try:
            attempt = ParsingAttempt(
                inn=inn,
                source_name=source_name,
                session_id=session_id,
                status=status,
                error_message=error_message,
                duration_ms=duration_ms
            )
            session.add(attempt)
            session.commit()
            session.refresh(attempt)
            return attempt
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_parsing_attempts(self, inn: str = None, source_name: str = None, 
                           session_id: int = None, limit: int = 100) -> List[ParsingAttempt]:
        session = self.get_session()
        try:
            query = session.query(ParsingAttempt)
            if inn:
                query = query.filter(ParsingAttempt.inn == inn)
            if source_name:
                query = query.filter(ParsingAttempt.source_name == source_name)
            if session_id:
                query = query.filter(ParsingAttempt.session_id == session_id)
            return query.order_by(ParsingAttempt.attempted_at.desc()).limit(limit).all()
        finally:
            session.close()
    
    def register_source(self, source_name: str, module_name: str, class_name: str, config: Dict[str, Any] = None) -> SourceRegistry:
        session = self.get_session()
        try:
            source = session.query(SourceRegistry).filter(SourceRegistry.source_name == source_name).first()
            if source:
                source.module_name = module_name
                source.class_name = class_name
                source.config = config or {}
                source.updated_at = datetime.utcnow()
            else:
                source = SourceRegistry(
                    source_name=source_name,
                    module_name=module_name,
                    class_name=class_name,
                    config=config or {}
                )
                session.add(source)
            session.commit()
            session.refresh(source)
            return source
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_registered_sources(self, enabled_only: bool = True) -> List[SourceRegistry]:
        session = self.get_session()
        try:
            query = session.query(SourceRegistry)
            if enabled_only:
                query = query.filter(SourceRegistry.enabled == 'true')
            return query.all()
        finally:
            session.close()
    
    def update_source_enabled(self, source_name: str, enabled: bool) -> None:
        session = self.get_session()
        try:
            source = session.query(SourceRegistry).filter(SourceRegistry.source_name == source_name).first()
            if source:
                source.enabled = 'true' if enabled else 'false'
                source.updated_at = datetime.utcnow()
                session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def close(self) -> None:
        if self.engine:
            self.engine.dispose()