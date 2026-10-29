"""Uji input valid dan penolakan konfigurasi sebelum kompilasi ACL."""

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import yaml

from src.compiler import ValidationError, load_inputs


ROOT = Path(__file__).resolve().parents[1]


class CompilerInputTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.policy_path = Path(temporary.name) / "policy.yaml"
        self.inventory_path = Path(temporary.name) / "vlans.yaml"
        self.policy = yaml.safe_load(
            (ROOT / "policies/campus.yaml").read_text(encoding="utf-8")
        )
        self.inventory = yaml.safe_load(
            (ROOT / "topology/vlans.yaml").read_text(encoding="utf-8")
        )

    def load(self):
        self.policy_path.write_text(
            yaml.safe_dump(self.policy, sort_keys=False), encoding="utf-8"
        )
        self.inventory_path.write_text(
            yaml.safe_dump(self.inventory, sort_keys=False), encoding="utf-8"
        )
        return load_inputs(self.policy_path, self.inventory_path)

    def assert_invalid(self, code, location):
        with self.assertRaises(ValidationError) as caught:
            self.load()
        error = caught.exception
        self.assertEqual(error.code, code)
        self.assertIn(location, error.location)
        self.assertIn(error.location, str(error))
        self.assertIn(code, str(error))
        self.assertTrue(error.message)

    def test_example_files_are_accepted_and_preserve_rule_order(self):
        policy, inventory = load_inputs(
            ROOT / "policies/campus.yaml", ROOT / "topology/vlans.yaml"
        )
        self.assertEqual(policy, self.policy)
        self.assertEqual(inventory, self.inventory)
        self.assertEqual(
            [rule["id"] for rule in policy["rules"]],
            ["staff-https", "guest-dns", "iot-mqtt"],
        )

    def test_explicit_deny_and_empty_rules_are_accepted(self):
        self.policy["rules"][0]["action"] = "deny"
        self.assertEqual(self.load()[0]["rules"][0]["action"], "deny")
        self.policy["rules"] = []
        self.assertEqual(self.load()[0]["rules"], [])

    def test_port_boundaries_and_unused_services_are_accepted(self):
        self.policy["services"]["boundaries"] = [
            {"protocol": "tcp", "destination_port": 1},
            {"protocol": "tcp", "destination_port": 65535},
        ]
        self.assertEqual(self.load()[0], self.policy)

    def test_versions_must_be_integer_one(self):
        for data, source in ((self.inventory, "vlans.yaml"), (self.policy, "policy.yaml")):
            for value in (True, "1", 1.0, 2, None):
                with self.subTest(source=source, value=value):
                    data["schema_version"] = value
                    self.assert_invalid("unsupported_version", source + ":schema_version")
            data["schema_version"] = 1

    def test_non_mapping_documents_are_rejected(self):
        original = self.policy
        for value in (None, [], "text", 1):
            with self.subTest(value=value):
                self.policy = value
                self.assert_invalid("invalid_type", "policy.yaml:root")
        self.policy = original
        for value in (None, [], "text", 1):
            with self.subTest(inventory=value):
                self.inventory = value
                self.assert_invalid("invalid_type", "vlans.yaml:root")

    def test_missing_and_unknown_fields_are_rejected_at_each_level(self):
        records = [
            (self.policy, "services"),
            (self.inventory, "vlans"),
            (self.inventory["vlans"][0], "gateway"),
            (self.policy["services"]["https"][0], "destination_port"),
            (self.policy["rules"][0], "action"),
        ]
        for record, field in records:
            with self.subTest(missing=field):
                value = record.pop(field)
                self.assert_invalid("missing_field", "." + field)
                record[field] = value
            with self.subTest(extra=field):
                record["unexpected"] = 1
                self.assert_invalid("unknown_field", ".unexpected")
                del record["unexpected"]

    def test_yaml_syntax_duplicate_keys_and_unsafe_tags_are_rejected(self):
        self.load()
        cases = [
            ("rules: [", "invalid_yaml"),
            ("schema_version: 1\nschema_version: 1\n", "duplicate_key"),
            ("services:\n  https:\n    - protocol: tcp\n      protocol: udp\n", "duplicate_key"),
            ("true: value\n", "invalid_key"),
            ("? [one, two]\n: value\n", "invalid_key"),
            ("base: &base {schema_version: 1}\n<<: *base\n", "invalid_key"),
            ("!!python/object/apply:builtins.eval ['1 + 1']\n", "invalid_yaml"),
            ("schema_version: 1\n---\nschema_version: 1\n", "invalid_yaml"),
        ]
        for text, code in cases:
            with self.subTest(text=text):
                self.policy_path.write_text(text, encoding="utf-8")
                with self.assertRaises(ValidationError) as caught:
                    load_inputs(self.policy_path, self.inventory_path)
                self.assertEqual(caught.exception.code, code)
                self.assertIn("policy.yaml:", caught.exception.location)

    def test_missing_file_and_invalid_utf8_have_clear_errors(self):
        self.load()
        self.policy_path.unlink()
        with self.assertRaises(ValidationError) as caught:
            load_inputs(self.policy_path, self.inventory_path)
        self.assertEqual(caught.exception.code, "read_error")
        self.assertEqual(caught.exception.location, str(self.policy_path))
        self.policy_path.write_bytes(b"\xff\xfe")
        with self.assertRaises(ValidationError) as caught:
            load_inputs(self.policy_path, self.inventory_path)
        self.assertEqual(caught.exception.code, "read_error")

    def test_recursive_alias_is_rejected_without_hanging(self):
        self.load()
        self.policy_path.write_text(
            "schema_version: 1\ndefault_action: deny\n"
            "services: {https: [{protocol: tcp, destination_port: 443}]}\n"
            "rules: &recursive [*recursive]\n", encoding="utf-8"
        )
        with self.assertRaises(ValidationError) as caught:
            load_inputs(self.policy_path, self.inventory_path)
        self.assertEqual(caught.exception.code, "invalid_type")
        self.assertIn("rules[0]", caught.exception.location)

    def test_vlan_ids_are_bounded_integers(self):
        for value in (0, 4095, True, "10", 10.0, None, []):
            with self.subTest(value=value):
                self.inventory["vlans"][0]["id"] = value
                self.assert_invalid("invalid_integer", "vlans[0].id")
        for value in (1, 4094):
            with self.subTest(valid=value):
                self.inventory["vlans"][0]["id"] = value
                self.policy["rules"][0]["source_vlan"] = value
                self.assertEqual(self.load()[1]["vlans"][0]["id"], value)

    def test_vlan_ids_and_names_are_unique(self):
        self.inventory["vlans"][1]["id"] = 10
        self.assert_invalid("duplicate_vlan_id", "vlans[1].id")
        self.inventory["vlans"][1]["id"] = 20
        self.inventory["vlans"][1]["name"] = "Staff"
        self.assert_invalid("duplicate_vlan_name", "vlans[1].name")

    def test_subnets_must_be_ipv4_networks_in_cidr_notation(self):
        for value in ("bad", "10.10.10.1/24", "::/0", "10.10.10.0", "10.10.10.0/255.255.255.0"):
            with self.subTest(value=value):
                self.inventory["vlans"][0]["subnet"] = value
                self.assert_invalid("invalid_subnet", "vlans[0].subnet")

    def test_overlapping_subnets_are_rejected(self):
        self.inventory["vlans"][1]["subnet"] = "10.10.10.0/25"
        self.inventory["vlans"][1]["gateway"] = "10.10.10.2"
        self.assert_invalid("overlapping_subnet", "vlans[1].subnet")

    def test_gateway_must_be_a_host_in_its_subnet(self):
        for value in ("10.10.20.1", "10.10.10.0", "10.10.10.255", "bad", "::1"):
            with self.subTest(value=value):
                self.inventory["vlans"][0]["gateway"] = value
                self.assert_invalid("invalid_gateway", "vlans[0].gateway")

    def test_names_and_ids_are_nonempty_strings_without_outer_whitespace(self):
        fields = [
            (self.inventory["vlans"][0], "name"),
            (self.inventory["vlans"][0], "subnet"),
            (self.inventory["vlans"][0], "gateway"),
            (self.policy["rules"][0], "id"),
            (self.policy["rules"][0], "service"),
        ]
        for record, field in fields:
            original = record[field]
            for value in ("", " value", "value ", 12, None):
                with self.subTest(field=field, value=value):
                    record[field] = value
                    self.assert_invalid("invalid_string", "." + field)
            record[field] = original

    def test_services_and_terms_must_be_nonempty(self):
        original = deepcopy(self.policy["services"])
        for value in ({}, [], None):
            with self.subTest(services=value):
                self.policy["services"] = value
                self.assert_invalid("invalid_type", ":services")
        self.policy["services"] = original
        for value in ([], {}, None):
            with self.subTest(terms=value):
                self.policy["services"]["https"] = value
                self.assert_invalid("invalid_type", "services.https")
        self.policy["services"]["https"] = [None]
        self.assert_invalid("invalid_type", "services.https[0]")

    def test_service_names_are_checked(self):
        terms = deepcopy(self.policy["services"]["https"])
        for name in ("", " https", "https "):
            with self.subTest(name=name):
                self.policy["services"] = {name: terms}
                self.assert_invalid("invalid_string", ":services")

    def test_protocols_are_tcp_or_udp(self):
        for value in ("icmp", "TCP", None, 53, ["tcp"], {"tcp": 1}):
            with self.subTest(value=value):
                self.policy["services"]["https"][0]["protocol"] = value
                self.assert_invalid("invalid_protocol", ".protocol")

    def test_ports_are_bounded_integers(self):
        for value in (0, 65536, True, "443", 443.0, None):
            with self.subTest(value=value):
                self.policy["services"]["https"][0]["destination_port"] = value
                self.assert_invalid("invalid_integer", ".destination_port")

    def test_duplicate_service_terms_are_rejected(self):
        self.policy["services"]["https"] *= 2
        self.assert_invalid("duplicate_service_term", "services.https[1]")

    def test_rule_vlan_references_and_types_are_checked(self):
        rule = self.policy["rules"][0]
        for field in ("source_vlan", "destination_vlan"):
            original = rule[field]
            for value, code in ((99, "unknown_vlan"), (True, "invalid_integer"), ("10", "invalid_integer")):
                with self.subTest(field=field, value=value):
                    rule[field] = value
                    self.assert_invalid(code, "." + field)
            rule[field] = original

    def test_service_reference_and_vlan_direction_are_checked(self):
        rule = self.policy["rules"][0]
        rule["service"] = "ssh"
        self.assert_invalid("unknown_service", ".service")
        rule["service"] = "https"
        rule["source_vlan"] = rule["destination_vlan"]
        self.assert_invalid("same_vlan", "rules[0]")

    def test_default_and_rule_actions_are_checked(self):
        for value in ("allow", None, True, ["deny"]):
            with self.subTest(default=value):
                self.policy["default_action"] = value
                self.assert_invalid("invalid_default_action", ":default_action")
        self.policy["default_action"] = "deny"
        for value in ("permit", "ALLOW", None, True, ["allow"]):
            with self.subTest(action=value):
                self.policy["rules"][0]["action"] = value
                self.assert_invalid("invalid_action", ".action")

    def test_rule_ids_are_unique(self):
        self.policy["rules"][1]["id"] = self.policy["rules"][0]["id"]
        self.assert_invalid("duplicate_rule_id", "rules[1].id")

    def test_vlan_and_rule_lists_have_correct_shapes(self):
        for value in (None, {}, [], "vlans"):
            with self.subTest(vlans=value):
                self.inventory["vlans"] = value
                self.assert_invalid("invalid_type", ":vlans")
        self.inventory = yaml.safe_load(
            (ROOT / "topology/vlans.yaml").read_text(encoding="utf-8")
        )
        for value in (None, {}, "rules"):
            with self.subTest(rules=value):
                self.policy["rules"] = value
                self.assert_invalid("invalid_type", ":rules")
        self.policy["rules"] = [None]
        self.assert_invalid("invalid_type", "rules[0]")


if __name__ == "__main__":
    unittest.main()
