from abc import ABC, abstractmethod
from typing import Dict, Any
import time


class BaseParser(ABC):
    def __init__(self, source_name: str, config: Dict[str, Any]):
        self.source_name = source_name
        self.config = config
        self.timeout = config.get('timeout', 30)
        self.retry_count = config.get('retry_count', 3)
        self.retry_delay = config.get('retry_delay', 2)
    
    @abstractmethod
    def parse(self, inn: str) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def get_data_schema(self) -> Dict[str, Any]:
        pass
    
    def parse_with_retry(self, inn: str) -> Dict[str, Any]:
        last_error = None
        for attempt in range(self.retry_count):
            try:
                start_time = time.time()
                result = self.parse(inn)
                duration_ms = int((time.time() - start_time) * 1000)
                
                result['_metadata'] = {
                    'source': self.source_name,
                    'attempt': attempt + 1,
                    'duration_ms': duration_ms,
                    'timestamp': time.time()
                }
                
                return result
                
            except Exception as e:
                last_error = str(e)
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                continue
        
        raise Exception(f"All retry attempts failed for {self.source_name}: {last_error}")
    
    def get_source_name(self) -> str:
        return self.source_name
    
    def normalize_inn(self, inn: str) -> str:
        return inn.replace(' ', '').replace('-', '').strip()