from typing import Any, Dict, List, Tuple


VOLATILE_KEYS = {
    'parsed_at',
    'extracted_at',
    '_metadata',
    'url',
}

INTERNAL_PREFIXES = ('_',)


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == '':
        return True
    if isinstance(value, (list, dict)) and len(value) == 0:
        return True
    return False


def _should_skip_key(key: str) -> bool:
    if key in VOLATILE_KEYS:
        return True
    for prefix in INTERNAL_PREFIXES:
        if key.startswith(prefix):
            return True
    return False


def _flatten(data: Any, prefix: str = '') -> Dict[str, Any]:
    flat: Dict[str, Any] = {}
    if isinstance(data, dict):
        for key, value in data.items():
            if _should_skip_key(key):
                continue
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                flat.update(_flatten(value, path))
            elif isinstance(value, list):
                if all(isinstance(v, (str, int, float, bool)) or v is None for v in value):
                    if not _is_empty(value):
                        flat[path] = value
                else:
                    for idx, item in enumerate(value):
                        flat.update(_flatten(item, f"{path}[{idx}]"))
            else:
                if not _is_empty(value):
                    flat[path] = value
    return flat


def compute_diff(old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    old_flat = _flatten(old) if isinstance(old, dict) else {}
    new_flat = _flatten(new) if isinstance(new, dict) else {}

    all_keys = set(old_flat.keys()) | set(new_flat.keys())

    changed_fields: List[Dict[str, Any]] = []

    for key in sorted(all_keys):
        old_val = old_flat.get(key)
        new_val = new_flat.get(key)

        if old_val == new_val:
            continue

        entry: Dict[str, Any] = {'field': key}

        if key in old_flat and key in new_flat:
            entry['type'] = 'changed'
            entry['from'] = old_val
            entry['to'] = new_val
        elif key in new_flat:
            entry['type'] = 'added'
            entry['to'] = new_val
        else:
            entry['type'] = 'removed'
            entry['from'] = old_val

        changed_fields.append(entry)

    return {
        'changed': len(changed_fields) > 0,
        'fields': changed_fields,
        'changed_count': len(changed_fields),
    }