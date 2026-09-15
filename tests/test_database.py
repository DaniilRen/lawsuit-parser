import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.db_manager import DatabaseManager
from src.database.models import Base, Company


class TestDatabaseManager:
    @pytest.fixture
    def db_manager(self):
        config = {
            'host': 'localhost',
            'port': 5432,
            'name': 'test_company_parser',
            'user': 'postgres',
            'password': 'postgres',
            'echo': False
        }
        
        engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(engine)
        
        db = DatabaseManager(config)
        db.engine = engine
        db.SessionLocal = sessionmaker(bind=engine)
        
        return db
    
    def test_insert_company(self, db_manager):
        company_data = {
            'inn': '1234567890',
            'name': 'Test Company',
            'legal_address': 'Test Address'
        }
        
        company = db_manager.insert_company(company_data)
        
        assert company.inn == '1234567890'
        assert company.name == 'Test Company'
        assert company.legal_address == 'Test Address'
    
    def test_get_company(self, db_manager):
        company_data = {
            'inn': '1234567890',
            'name': 'Test Company',
            'legal_address': 'Test Address'
        }
        
        db_manager.insert_company(company_data)
        
        company = db_manager.get_company('1234567890')
        
        assert company is not None
        assert company.inn == '1234567890'
        assert company.name == 'Test Company'
    
    def test_update_company(self, db_manager):
        company_data = {
            'inn': '1234567890',
            'name': 'Old Name',
            'legal_address': 'Old Address'
        }
        
        db_manager.insert_company(company_data)
        
        update_data = {
            'name': 'New Name',
            'legal_address': 'New Address',
            'status': 'inactive'
        }
        
        updated = db_manager.update_company('1234567890', update_data)
        
        assert updated is not None
        assert updated.name == 'New Name'
        assert updated.legal_address == 'New Address'
        assert updated.status == 'inactive'