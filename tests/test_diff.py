from src.utils.diff import compute_diff


class TestComputeDiff:
    def test_no_changes(self):
        old = {'name': 'Acme', 'address': 'Street 1'}
        new = {'name': 'Acme', 'address': 'Street 1'}
        result = compute_diff(old, new)
        assert result['changed'] is False
        assert result['fields'] == []
        assert result['changed_count'] == 0

    def test_changed_value(self):
        old = {'name': 'Acme', 'status': 'active'}
        new = {'name': 'Acme', 'status': 'liquidating'}
        result = compute_diff(old, new)
        assert result['changed'] is True
        assert result['changed_count'] == 1
        field = result['fields'][0]
        assert field['field'] == 'status'
        assert field['type'] == 'changed'
        assert field['from'] == 'active'
        assert field['to'] == 'liquidating'

    def test_added_field(self):
        old = {'name': 'Acme'}
        new = {'name': 'Acme', 'inn': '7707083893'}
        result = compute_diff(old, new)
        assert result['changed'] is True
        field = result['fields'][0]
        assert field['field'] == 'inn'
        assert field['type'] == 'added'
        assert field['to'] == '7707083893'

    def test_removed_field(self):
        old = {'name': 'Acme', 'inn': '7707083893'}
        new = {'name': 'Acme'}
        result = compute_diff(old, new)
        assert result['changed'] is True
        field = result['fields'][0]
        assert field['field'] == 'inn'
        assert field['type'] == 'removed'
        assert field['from'] == '7707083893'

    def test_nested_change(self):
        old = {'director': {'name': 'Ivanov', 'position': 'CEO'}}
        new = {'director': {'name': 'Petrov', 'position': 'CEO'}}
        result = compute_diff(old, new)
        assert result['changed'] is True
        assert result['fields'][0]['field'] == 'director.name'

    def test_volatile_keys_ignored(self):
        old = {'name': 'Acme', 'parsed_at': '2026-01-01', 'url': 'http://a'}
        new = {'name': 'Acme', 'parsed_at': '2026-09-15', 'url': 'http://b'}
        result = compute_diff(old, new)
        assert result['changed'] is False

    def test_internal_keys_ignored(self):
        old = {'name': 'Acme', '_metadata': {'attempt': 1}}
        new = {'name': 'Acme', '_metadata': {'attempt': 2}}
        result = compute_diff(old, new)
        assert result['changed'] is False

    def test_empty_values_ignored(self):
        old = {'name': 'Acme', 'address': ''}
        new = {'name': 'Acme', 'address': None}
        result = compute_diff(old, new)
        assert result['changed'] is False

    def test_list_of_primitives(self):
        old = {'tags': ['a', 'b']}
        new = {'tags': ['a', 'b', 'c']}
        result = compute_diff(old, new)
        assert result['changed'] is True
        assert result['fields'][0]['field'] == 'tags'

    def test_list_of_dicts_indexed(self):
        old = {'items': [{'id': 1, 'value': 'a'}]}
        new = {'items': [{'id': 1, 'value': 'b'}]}
        result = compute_diff(old, new)
        assert result['changed'] is True
        assert result['fields'][0]['field'] == 'items[0].value'

    def test_multiple_changes_sorted(self):
        old = {'a': 1, 'b': 2, 'c': 3}
        new = {'a': 10, 'b': 20, 'c': 30}
        result = compute_diff(old, new)
        assert result['changed_count'] == 3
        fields = [f['field'] for f in result['fields']]
        assert fields == ['a', 'b', 'c']