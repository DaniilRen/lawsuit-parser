from typing import Any, Dict, List, Optional

from src.database.db_manager import DatabaseManager
from src.database.models import Company, ParserData, ParsingSession, SourceRegistry


class QueryService:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def list_companies(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        session = self.db.get_session()
        try:
            total = session.query(Company).count()
            rows = (
                session.query(Company)
                .order_by(Company.created_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            items = []
            for company in rows:
                last_parsed = (
                    session.query(ParserData)
                    .filter(ParserData.inn == company.inn)
                    .order_by(ParserData.parsed_at.desc())
                    .first()
                )
                items.append({
                    'inn': company.inn,
                    'first_parsed_at': company.created_at.isoformat() if company.created_at else None,
                    'last_parsed_at': last_parsed.parsed_at.isoformat() if last_parsed else None,
                })
            return {'items': items, 'total': total, 'limit': limit, 'offset': offset}
        finally:
            session.close()

    def get_company(self, inn: str) -> Optional[Dict[str, Any]]:
        session = self.db.get_session()
        try:
            company = session.query(Company).filter(Company.inn == inn).first()
            if not company:
                return None

            data_rows = (
                session.query(ParserData)
                .filter(ParserData.inn == inn)
                .order_by(ParserData.parsed_at.desc())
                .all()
            )

            source_names = sorted({row.source_name for row in data_rows})
            last_parsed = data_rows[0].parsed_at.isoformat() if data_rows else None

            return {
                'inn': inn,
                'first_parsed_at': company.created_at.isoformat() if company.created_at else None,
                'last_parsed_at': last_parsed,
                'sessions_count': len({row.session_id for row in data_rows}),
                'sources': source_names,
            }
        finally:
            session.close()

    def get_latest(self, inn: str, sources: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        session = self.db.get_session()
        try:
            company = session.query(Company).filter(Company.inn == inn).first()
            if not company:
                return None

            query = session.query(ParserData).filter(ParserData.inn == inn)
            if sources:
                query = query.filter(ParserData.source_name.in_(sources))

            rows = query.order_by(ParserData.parsed_at.desc()).all()

            latest_per_source: Dict[str, Dict[str, Any]] = {}
            session_id_for_latest: Optional[int] = None

            for row in rows:
                if row.source_name in latest_per_source:
                    continue
                latest_per_source[row.source_name] = row.data
                if session_id_for_latest is None:
                    session_id_for_latest = row.session_id

            return {
                'inn': inn,
                'session_id': session_id_for_latest,
                'sources': latest_per_source,
            }
        finally:
            session.close()

    def get_history(
        self,
        inn: str,
        sources: Optional[List[str]] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        session = self.db.get_session()
        try:
            query = session.query(ParserData).filter(ParserData.inn == inn)
            if sources:
                query = query.filter(ParserData.source_name.in_(sources))

            rows = query.order_by(ParserData.parsed_at.desc()).all()

            sessions_map: Dict[int, Dict[str, Any]] = {}
            for row in rows:
                sid = row.session_id
                if sid not in sessions_map:
                    sessions_map[sid] = {
                        'session_id': sid,
                        'parsed_at': row.parsed_at.isoformat() if row.parsed_at else None,
                        'sources': [],
                    }
                if row.source_name not in sessions_map[sid]['sources']:
                    sessions_map[sid]['sources'].append(row.source_name)

            ordered = sorted(sessions_map.values(), key=lambda s: s['session_id'], reverse=True)
            total = len(ordered)
            page = ordered[offset:offset + limit]

            return {'items': page, 'total': total, 'limit': limit, 'offset': offset}
        finally:
            session.close()

    def get_session_data_for_inn(self, inn: str, session_id: int) -> List[Dict[str, Any]]:
        session = self.db.get_session()
        try:
            rows = (
                session.query(ParserData)
                .filter(ParserData.inn == inn, ParserData.session_id == session_id)
                .all()
            )
            return [
                {
                    'source': row.source_name,
                    'session_id': row.session_id,
                    'parsed_at': row.parsed_at.isoformat() if row.parsed_at else None,
                    'data': row.data,
                }
                for row in rows
            ]
        finally:
            session.close()

    def get_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        session = self.db.get_session()
        try:
            row = session.query(ParsingSession).filter(ParsingSession.id == session_id).first()
            if not row:
                return None
            return {
                'session_id': row.id,
                'started_at': row.started_at.isoformat() if row.started_at else None,
                'completed_at': row.completed_at.isoformat() if row.completed_at else None,
                'status': row.status,
                'total_sources': row.total_sources,
                'successful_sources': row.successful_sources,
            }
        finally:
            session.close()

    def list_sessions(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        session = self.db.get_session()
        try:
            total = session.query(ParsingSession).count()
            rows = (
                session.query(ParsingSession)
                .order_by(ParsingSession.started_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            items = [
                {
                    'session_id': row.id,
                    'started_at': row.started_at.isoformat() if row.started_at else None,
                    'completed_at': row.completed_at.isoformat() if row.completed_at else None,
                    'status': row.status,
                    'total_sources': row.total_sources,
                    'successful_sources': row.successful_sources,
                }
                for row in rows
            ]
            return {'items': items, 'total': total, 'limit': limit, 'offset': offset}
        finally:
            session.close()

    def get_session_data(self, session_id: int) -> Optional[Dict[str, Any]]:
        session = self.db.get_session()
        try:
            session_row = session.query(ParsingSession).filter(ParsingSession.id == session_id).first()
            if not session_row:
                return None

            rows = session.query(ParserData).filter(ParserData.session_id == session_id).all()
            items = [
                {
                    'inn': row.inn,
                    'source': row.source_name,
                    'parsed_at': row.parsed_at.isoformat() if row.parsed_at else None,
                    'data': row.data,
                }
                for row in rows
            ]

            return {
                'session_id': session_id,
                'started_at': session_row.started_at.isoformat() if session_row.started_at else None,
                'completed_at': session_row.completed_at.isoformat() if session_row.completed_at else None,
                'status': session_row.status,
                'items': items,
            }
        finally:
            session.close()

    def list_registered_sources(self) -> List[Dict[str, Any]]:
        session = self.db.get_session()
        try:
            rows = session.query(SourceRegistry).order_by(SourceRegistry.source_name).all()
            return [
                {
                    'source_name': row.source_name,
                    'module_name': row.module_name,
                    'class_name': row.class_name,
                    'enabled': row.enabled == 'true',
                }
                for row in rows
            ]
        finally:
            session.close()