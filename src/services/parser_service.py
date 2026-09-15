from typing import Dict, Any, Optional, List
import asyncio
import time
from datetime import datetime

from src.database.db_manager import DatabaseManager
from src.parsers.parser_factory import ParserFactory
from src.utils.logger import setup_logger


class ParserService:
    def __init__(self, db_manager: DatabaseManager, config_manager):
        self.db = db_manager
        self.config_manager = config_manager
        self.parser_factory = ParserFactory(config_manager)
        self.logger = setup_logger()
        
        processing_config = config_manager.get_processing_config()
        self.parallel = processing_config.get('parallel_sources', False)
        self.max_workers = processing_config.get('max_workers', 3)
        self.timeout_per_source = processing_config.get('timeout_per_source', 60)
    
    async def parse_company(self, inn: str, source_name: str = None, parallel: bool = None) -> Dict[str, Any]:
        if parallel is None:
            parallel = self.parallel
        
        inn = inn.replace(' ', '').replace('-', '').strip()
        
        parsing_session = self.db.create_parsing_session()
        session_id = parsing_session.id
        
        try:
            if source_name:
                result = await self._parse_single_source(inn, source_name, session_id)
                self.db.complete_parsing_session(session_id, 1, 1 if result.get('success') else 0)
                return result
            else:
                if parallel:
                    results = await self._parse_all_sources_parallel(inn, session_id)
                else:
                    results = await self._parse_all_sources_sequential(inn, session_id)
                
                successful = sum(1 for r in results.values() if r.get('success'))
                self.db.complete_parsing_session(session_id, len(results), successful)
                
                return {
                    'success': successful > 0,
                    'session_id': session_id,
                    'total_sources': len(results),
                    'successful_sources': successful,
                    'results': results
                }
                
        except Exception as e:
            self.logger.error(f"Error parsing INN {inn}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def _parse_single_source(self, inn: str, source_name: str, session_id: int) -> Dict[str, Any]:
        parser = self.parser_factory.get_parser(source_name)
        if not parser:
            self.logger.warning(f"Parser not available for source: {source_name}")
            return {'success': False, 'error': f'Parser not available for source: {source_name}', 'source': source_name}
        
        start_time = time.time()
        try:
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, parser.parse_with_retry, inn),
                timeout=self.timeout_per_source
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            self.db.get_or_create_company(inn)
            self.db.save_parser_data(inn, source_name, session_id, result)
            self.db.add_parsing_attempt(inn, source_name, session_id, 'success', duration_ms=duration_ms)
            
            return {'success': True, 'data': result, 'source': source_name, 'session_id': session_id}
                
        except asyncio.TimeoutError:
            duration_ms = int((time.time() - start_time) * 1000)
            self.db.add_parsing_attempt(inn, source_name, session_id, 'error', 
                                      error_message='Timeout', duration_ms=duration_ms)
            return {'success': False, 'error': 'Timeout', 'source': source_name}
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.db.add_parsing_attempt(inn, source_name, session_id, 'error', 
                                      error_message=str(e), duration_ms=duration_ms)
            return {'success': False, 'error': str(e), 'source': source_name}
    
    async def _parse_all_sources_sequential(self, inn: str, session_id: int) -> Dict[str, Any]:
        parsers = self.parser_factory.get_all_parsers(enabled_only=True)
        results = {}
        
        for source_name in parsers:
            result = await self._parse_single_source(inn, source_name, session_id)
            results[source_name] = result
        
        return results
    
    async def _parse_all_sources_parallel(self, inn: str, session_id: int) -> Dict[str, Any]:
        parsers = self.parser_factory.get_all_parsers(enabled_only=True)
        
        if not parsers:
            return {}
        
        tasks = []
        for source_name in parsers:
            task = asyncio.create_task(self._parse_single_source(inn, source_name, session_id))
            tasks.append((source_name, task))
        
        results = {}
        for source_name, task in tasks:
            try:
                result = await task
                results[source_name] = result
            except Exception as e:
                results[source_name] = {'success': False, 'error': str(e), 'source': source_name}
        
        return results
    
    def parse_company_sync(self, inn: str, source_name: str = None, parallel: bool = None) -> Dict[str, Any]:
        return asyncio.run(self.parse_company(inn, source_name, parallel))
    
    def get_company_history(self, inn: str, source_name: str = None) -> List[Dict[str, Any]]:
        parser_data = self.db.get_parser_data(inn, source_name)
        return [{
            'source': pd.source_name,
            'session_id': pd.session_id,
            'data': pd.data,
            'parsed_at': pd.parsed_at.isoformat()
        } for pd in parser_data]
    
    def get_comparison(self, inn: str, session_id_1: int, session_id_2: int) -> Dict[str, Any]:
        data_1 = self.db.get_parser_data(inn, session_id=session_id_1)
        data_2 = self.db.get_parser_data(inn, session_id=session_id_2)
        
        comparison = {}
        
        for pd1 in data_1:
            source = pd1.source_name
            pd2 = next((d for d in data_2 if d.source_name == source), None)
            
            comparison[source] = {
                'session_1': pd1.data if pd1 else None,
                'session_2': pd2.data if pd2 else None,
                'changed': pd1.data != pd2.data if pd2 else True
            }
        
        return {
            'inn': inn,
            'session_1': session_id_1,
            'session_2': session_id_2,
            'comparison': comparison
        }