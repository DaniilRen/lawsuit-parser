from datetime import datetime

from src.database.models import (
    Company, ParserData, ParsingSession, ParsingAttempt, SourceRegistry,
)


def test_company_can_be_created(in_memory_db):
    Session = in_memory_db['session_factory']
    session = Session()

    company = Company(inn='7707083893')
    session.add(company)
    session.commit()

    stored = session.query(Company).filter(Company.inn == '7707083893').first()
    assert stored is not None
    assert stored.inn == '7707083893'

    session.close()


def test_parsing_session_has_defaults(in_memory_db):
    Session = in_memory_db['session_factory']
    session = Session()

    ps = ParsingSession()
    session.add(ps)
    session.commit()

    assert ps.id is not None
    assert ps.status == 'running'
    assert ps.started_at is not None

    session.close()


def test_parser_data_linked_to_company_and_session(in_memory_db):
    Session = in_memory_db['session_factory']
    session = Session()

    session.add(Company(inn='7707083893'))
    ps = ParsingSession()
    session.add(ps)
    session.commit()

    pd = ParserData(
        inn='7707083893',
        source_name='nalog',
        session_id=ps.id,
        data={'company_name': 'Test', 'status': 'active'},
    )
    session.add(pd)
    session.commit()

    stored = session.query(ParserData).filter(ParserData.inn == '7707083893').first()
    assert stored is not None
    assert stored.source_name == 'nalog'
    assert stored.data['company_name'] == 'Test'

    session.close()


def test_parsing_attempt_records_status(in_memory_db):
    Session = in_memory_db['session_factory']
    session = Session()

    ps = ParsingSession()
    session.add(ps)
    session.commit()

    attempt = ParsingAttempt(
        inn='7707083893',
        source_name='nalog',
        session_id=ps.id,
        status='success',
        duration_ms=1500,
    )
    session.add(attempt)
    session.commit()

    stored = session.query(ParsingAttempt).first()
    assert stored.status == 'success'
    assert stored.duration_ms == 1500

    session.close()


def test_source_registry_can_store_sources(in_memory_db):
    Session = in_memory_db['session_factory']
    session = Session()

    src = SourceRegistry(
        source_name='nalog',
        module_name='nalog_parser',
        class_name='NalogParser',
        enabled='true',
    )
    session.add(src)
    session.commit()

    stored = session.query(SourceRegistry).first()
    assert stored.source_name == 'nalog'
    assert stored.enabled == 'true'

    session.close()


def test_multiple_sessions_are_isolated(in_memory_db):
    """Two sessions for the same INN must not mix their data."""
    Session = in_memory_db['session_factory']
    session = Session()

    session.add(Company(inn='7707083893'))
    s1 = ParsingSession()
    s2 = ParsingSession()
    session.add_all([s1, s2])
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

    session.close()