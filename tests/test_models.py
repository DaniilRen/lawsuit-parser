import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import (
    Base, Company, ParserData, ParsingSession, ParsingAttempt, SourceRegistry,
)


@pytest.fixture
def session():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


def test_company_creation(session):
    c = Company(inn='7707083893')
    session.add(c)
    session.commit()
    assert session.query(Company).count() == 1
    assert session.query(Company).first().inn == '7707083893'


def test_parsing_session_defaults(session):
    s = ParsingSession()
    session.add(s)
    session.commit()
    assert s.id is not None
    assert s.status == 'running'


def test_parser_data_linked_to_session_and_company(session):
    session.add(Company(inn='7707083893'))
    s = ParsingSession()
    session.add(s)
    session.commit()

    pd = ParserData(
        inn='7707083893',
        source_name='nalog',
        session_id=s.id,
        data={'company_name': 'Test', 'status': 'active'},
    )
    session.add(pd)
    session.commit()

    assert session.query(ParserData).count() == 1
    row = session.query(ParserData).first()
    assert row.source_name == 'nalog'
    assert row.data['company_name'] == 'Test'


def test_parsing_attempt(session):
    s = ParsingSession()
    session.add(s)
    session.commit()

    a = ParsingAttempt(
        inn='7707083893',
        source_name='nalog',
        session_id=s.id,
        status='success',
        duration_ms=1500,
    )
    session.add(a)
    session.commit()
    assert a.status == 'success'
    assert a.duration_ms == 1500


def test_source_registry(session):
    r = SourceRegistry(
        source_name='nalog',
        module_name='nalog_parser',
        class_name='NalogParser',
        enabled='true',
    )
    session.add(r)
    session.commit()
    assert session.query(SourceRegistry).count() == 1
    assert session.query(SourceRegistry).first().source_name == 'nalog'


def test_session_data_isolation(session):
    s1 = ParsingSession()
    s2 = ParsingSession()
    session.add_all([s1, s2])
    session.add(Company(inn='7707083893'))
    session.commit()

    session.add_all([
        ParserData(inn='7707083893', source_name='nalog', session_id=s1.id, data={'a': 1}),
        ParserData(inn='7707083893', source_name='nalog', session_id=s2.id, data={'a': 2}),
    ])
    session.commit()

    s1_rows = session.query(ParserData).filter(ParserData.session_id == s1.id).all()
    s2_rows = session.query(ParserData).filter(ParserData.session_id == s2.id).all()
    assert s1_rows[0].data == {'a': 1}
    assert s2_rows[0].data == {'a': 2}