import copy
import random
from typing import Any, Dict, List, Optional

from src.config.config_manager import ConfigManager


RANDOM_STRINGS = [
    'Тестовое значение A',
    'Тестовое значение B',
    'Тестовое значение C',
    'Тестовое значение D',
]


def apply_simulation(
    source_name: str,
    old_data: Optional[Dict[str, Any]],
    new_data: Optional[Dict[str, Any]],
    config_manager: ConfigManager,
) -> tuple:
    """Return (old_data, new_data) possibly mutated to force a diff.

    Only affects the copy passed to compute_diff. The caller's originals
    are not modified. If the simulation is disabled or the source is not
    configured, returns the inputs unchanged.
    """
    testing = config_manager.get_config().get('testing', {}) if hasattr(config_manager, 'get_config') else {}
    sim = testing.get('simulate_changes', {})

    if not sim.get('enabled', False):
        return old_data, new_data

    if source_name not in sim.get('sources', {}):
        return old_data, new_data

    probability = float(sim.get('probability', 1.0))
    if random.random() > probability:
        return old_data, new_data

    fields: List[str] = sim['sources'][source_name].get('fields', [])
    if not fields:
        return old_data, new_data

    new_copy = copy.deepcopy(new_data) if new_data is not None else None
    if new_copy is None:
        return old_data, new_data

    for field in fields:
        new_copy[field] = _random_value(new_copy.get(field))

    return old_data, new_copy


def _random_value(current: Any) -> Any:
    if isinstance(current, bool):
        return not current
    if isinstance(current, (int, float)):
        return current + random.randint(1, 100)
    if isinstance(current, list):
        return current + [random.choice(RANDOM_STRINGS)]
    if isinstance(current, str):
        suffix = f' (изм. {random.randint(1000, 9999)})'
        return f'{current}{suffix}'
    if current is None:
        return random.choice(RANDOM_STRINGS)
    return random.choice(RANDOM_STRINGS)