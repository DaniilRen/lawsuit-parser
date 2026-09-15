import argparse
import asyncio
import json
import sys
from typing import List

from src.config.config_manager import ConfigManager
from src.database.db_manager import DatabaseManager
from src.services.parser_service import ParserService
from src.utils.logger import setup_logger
from src.utils.validators import validate_inn


def parse_arguments():
    parser = argparse.ArgumentParser(description="Company Info Parser")
    parser.add_argument("--parse-inn", type=str, help="Parse single INN")
    parser.add_argument("--parse-file", type=str, help="Parse INNs from file")
    parser.add_argument("--init-db", action="store_true", help="Initialize database")
    parser.add_argument("--config", type=str, default="src/config/settings.json", help="Config path")
    parser.add_argument("--source", type=str, help="Specific source to use")
    parser.add_argument("--parallel", action="store_true", help="Parse in parallel")
    parser.add_argument("--list-sources", action="store_true", help="List available sources")
    parser.add_argument("--history", type=str, help="Get parsing history for INN")
    parser.add_argument("--output", "-o", type=str, help="Save output to JSON file (works with --history)")
    parser.add_argument("--compare", nargs=3, metavar=('INN', 'SESSION_1', 'SESSION_2'),
                        help="Compare two parsing sessions")
    parser.add_argument("--version", action="version", version="Company Info Parser v0.1.0")
    return parser.parse_args()


async def parse_single_inn(inn: str, config_path: str, source: str = None, parallel: bool = False):
    logger = setup_logger()

    if not validate_inn(inn):
        logger.error(f"Invalid INN format: {inn}")
        return False

    try:
        config = ConfigManager(config_path)
        db = DatabaseManager(config.get_db_config())
        service = ParserService(db, config)

        result = await service.parse_company(inn, source, parallel)

        if result.get('success'):
            logger.info(f"Successfully parsed INN: {inn}")
            logger.info(f"Session ID: {result.get('session_id', 'N/A')}")
            return True
        else:
            logger.error(f"Failed to parse INN: {inn} - {result.get('error', 'Unknown error')}")
            return False

    except Exception as e:
        logger.error(f"Error parsing INN {inn}: {str(e)}")
        return False


async def parse_from_file(file_path: str, config_path: str, source: str = None, parallel: bool = False):
    logger = setup_logger()

    try:
        with open(file_path, 'r') as f:
            inns = [line.strip() for line in f if line.strip()]

        logger.info(f"Found {len(inns)} INNs to parse")

        results = []
        for inn in inns:
            result = await parse_single_inn(inn, config_path, source, parallel)
            results.append(result)

        success_count = sum(results)
        logger.info(f"Parsed {success_count}/{len(inns)} INNs successfully")
        return success_count == len(inns)

    except Exception as e:
        logger.error(f"Error reading file {file_path}: {str(e)}")
        return False


async def init_database(config_path: str):
    logger = setup_logger()

    try:
        config = ConfigManager(config_path)
        db = DatabaseManager(config.get_db_config())
        db.create_tables()

        enabled_sources = config.get_enabled_sources()
        for source_name, source_config in enabled_sources.items():
            db.register_source(
                source_name,
                source_config.get('module', ''),
                source_config.get('class', ''),
                source_config
            )

        logger.info("Database initialized successfully")
        logger.info(f"Registered {len(enabled_sources)} sources")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        return False


async def list_sources(config_path: str):
    logger = setup_logger()

    try:
        config = ConfigManager(config_path)
        sources = config.get_sources()

        print("\nAvailable Sources:")
        print("-" * 60)
        print(f"{'Source':<20} {'Enabled':<10} {'Module':<20} {'Class':<20}")
        print("-" * 60)

        for name, cfg in sources.items():
            print(f"{name:<20} {str(cfg.get('enabled', False)):<10} "
                  f"{cfg.get('module', 'N/A'):<20} {cfg.get('class', 'N/A'):<20}")
        print("-" * 60)
        print(f"Total: {len(sources)} sources, "
              f"{len([s for s in sources.values() if s.get('enabled', False)])} enabled")

        return True
    except Exception as e:
        logger.error(f"Error listing sources: {str(e)}")
        return False


async def show_history(inn: str, config_path: str, output: str = None):
    logger = setup_logger()

    if not validate_inn(inn):
        logger.error(f"Invalid INN format: {inn}")
        return False

    try:
        config = ConfigManager(config_path)
        db = DatabaseManager(config.get_db_config())
        service = ParserService(db, config)

        history = service.get_company_history(inn)

        if not history:
            print(f"\nNo history found for INN: {inn}")
            if output:
                with open(output, 'w', encoding='utf-8') as f:
                    json.dump({
                        "inn": inn,
                        "total_sessions": 0,
                        "total_entries": 0,
                        "sessions": []
                    }, f, indent=2, ensure_ascii=False)
                print(f"Empty result saved to: {output}")
            return True

        if output:
            return _save_history_to_file(inn, history, output)

        print(f"\nHistory for INN: {inn}")
        print("=" * 80)

        current_session = None
        for entry in history:
            if entry['session_id'] != current_session:
                current_session = entry['session_id']
                print(f"\nSession: {current_session}")
                print(f"Parsed at: {entry['parsed_at']}")
                print("-" * 40)

            print(f"Source: {entry['source']}")
            print(f"Data: {entry['data']}")
            print()

        return True

    except Exception as e:
        logger.error(f"Error showing history for {inn}: {str(e)}")
        return False


def _save_history_to_file(inn: str, history: list, output: str) -> bool:
    sessions = {}

    for entry in history:
        sid = entry['session_id']
        if sid not in sessions:
            sessions[sid] = {
                'session_id': sid,
                'parsed_at': entry['parsed_at'],
                'sources': {}
            }
        sessions[sid]['sources'][entry['source']] = entry['data']

    sorted_sessions = sorted(sessions.values(), key=lambda s: s['session_id'])

    result = {
        'inn': inn,
        'total_sessions': len(sorted_sessions),
        'total_entries': len(history),
        'sessions': sorted_sessions,
    }

    with open(output, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"History for INN {inn} saved to: {output}")
    print(f"  Sessions: {len(sorted_sessions)}")
    print(f"  Total entries: {len(history)}")

    return True


async def compare_sessions(inn: str, session_1: str, session_2: str, config_path: str):
    logger = setup_logger()

    if not validate_inn(inn):
        logger.error(f"Invalid INN format: {inn}")
        return False

    try:
        config = ConfigManager(config_path)
        db = DatabaseManager(config.get_db_config())
        service = ParserService(db, config)

        comparison = service.get_comparison(inn, int(session_1), int(session_2))

        print(f"\nComparison for INN: {inn}")
        print(f"Session 1: {session_1}, Session 2: {session_2}")
        print("=" * 80)

        for source, data in comparison['comparison'].items():
            print(f"\nSource: {source}")
            print(f"Changed: {data['changed']}")
            if data['changed']:
                print("Session 1 Data:", data['session_1'])
                print("Session 2 Data:", data['session_2'])
            else:
                print("Data:", data['session_1'])

        return True

    except Exception as e:
        logger.error(f"Error comparing sessions: {str(e)}")
        return False


async def main():
    args = parse_arguments()

    if args.list_sources:
        await list_sources(args.config)
        return

    if args.init_db:
        await init_database(args.config)
        return

    if args.history:
        await show_history(args.history, args.config, args.output)
        return

    if args.compare:
        await compare_sessions(args.compare[0], args.compare[1], args.compare[2], args.config)
        return

    if args.parse_inn:
        await parse_single_inn(args.parse_inn, args.config, args.source, args.parallel)
        return

    if args.parse_file:
        await parse_from_file(args.parse_file, args.config, args.source, args.parallel)
        return

    print("No action specified. Use --help for usage information.")


if __name__ == "__main__":
    asyncio.run(main())