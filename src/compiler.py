"""Pembacaan dan validasi input versi 1; rendering ACL belum diimplementasikan."""

from ipaddress import IPv4Address, IPv4Network
from pathlib import Path

import yaml


class ValidationError(ValueError):
    """Kesalahan input dengan kode, lokasi, dan alasan yang dapat dilaporkan."""

    def __init__(self, code: str, location: str, message: str):
        self.code = code
        self.location = location
        self.message = message
        super().__init__(f"{location}: [{code}] {message}")


def _read_yaml(path: str | Path):
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ValidationError("read_error", str(path), str(error)) from error

    try:
        # safe_load menerima key duplikat; periksa node sebelum konstruksi nilai.
        pending = [yaml.compose(text, Loader=yaml.SafeLoader)]
        visited = set()
        while pending:
            node = pending.pop()
            if node is None or id(node) in visited:
                continue
            visited.add(id(node))
            if isinstance(node, yaml.MappingNode):
                keys = set()
                for key, value in node.value:
                    location = f"{path}:{key.start_mark.line + 1}:{key.start_mark.column + 1}"
                    if not isinstance(key, yaml.ScalarNode) or key.tag != "tag:yaml.org,2002:str":
                        raise ValidationError("invalid_key", location, "Key YAML harus string; merge key tidak didukung.")
                    if key.value in keys:
                        raise ValidationError("duplicate_key", location, f"Key YAML duplikat: {key.value}.")
                    keys.add(key.value)
                    pending.append(value)
            elif isinstance(node, yaml.SequenceNode):
                pending.extend(node.value)
        return yaml.safe_load(text)
    except (yaml.YAMLError, RecursionError) as error:
        mark = getattr(error, "problem_mark", None)
        location = str(path) if mark is None else f"{path}:{mark.line + 1}:{mark.column + 1}"
        message = getattr(error, "problem", None) or "YAML tidak valid atau bersarang terlalu dalam."
        raise ValidationError("invalid_yaml", location, message) from error


def _object(value, fields: set[str], location: str):
    if not isinstance(value, dict):
        raise ValidationError("invalid_type", location, "Harus berupa mapping YAML.")
    missing = fields - value.keys()
    extra = value.keys() - fields
    if missing:
        field = sorted(missing)[0]
        raise ValidationError("missing_field", f"{location}.{field}", "Field wajib belum diisi.")
    if extra:
        field = sorted(extra)[0]
        raise ValidationError("unknown_field", f"{location}.{field}", "Field tidak dikenal pada versi 1.")


def _string(value, location: str):
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValidationError("invalid_string", location, "Harus string tidak kosong tanpa spasi awal/akhir.")


def _integer(value, minimum: int, maximum: int, location: str):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValidationError("invalid_integer", location, f"Harus integer {minimum}-{maximum}, bukan boolean atau string.")


def _list(value, location: str, *, nonempty: bool = True):
    if not isinstance(value, list) or (nonempty and not value):
        message = "Harus list tidak kosong." if nonempty else "Harus berupa list."
        raise ValidationError("invalid_type", location, message)


def _version(data: dict, source: str):
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ValidationError("unsupported_version", f"{source}:schema_version", "Versi yang didukung adalah integer 1.")


def _validate_inventory(data, source: str):
    _object(data, {"schema_version", "vlans"}, f"{source}:root")
    _version(data, source)
    _list(data["vlans"], f"{source}:vlans")
    ids, names, networks = set(), set(), []
    for index, vlan in enumerate(data["vlans"]):
        location = f"{source}:vlans[{index}]"
        _object(vlan, {"id", "name", "subnet", "gateway"}, location)
        _integer(vlan["id"], 1, 4094, f"{location}.id")
        _string(vlan["name"], f"{location}.name")
        if vlan["id"] in ids:
            raise ValidationError("duplicate_vlan_id", f"{location}.id", f"ID VLAN {vlan['id']} sudah dipakai.")
        if vlan["name"] in names:
            raise ValidationError("duplicate_vlan_name", f"{location}.name", f"Nama VLAN {vlan['name']} sudah dipakai.")
        _string(vlan["subnet"], f"{location}.subnet")
        try:
            _, separator, prefix = vlan["subnet"].partition("/")
            if not separator or not prefix.isascii() or not prefix.isdecimal():
                raise ValueError("Gunakan prefix CIDR numerik, misalnya /24.")
            network = IPv4Network(vlan["subnet"], strict=True)
        except ValueError as error:
            raise ValidationError("invalid_subnet", f"{location}.subnet", f"Subnet harus CIDR IPv4 dengan alamat network yang benar: {error}") from error
        for previous_id, previous in networks:
            if network.overlaps(previous):
                raise ValidationError("overlapping_subnet", f"{location}.subnet", f"Subnet bertumpang tindih dengan VLAN {previous_id} ({previous}).")
        _string(vlan["gateway"], f"{location}.gateway")
        try:
            gateway = IPv4Address(vlan["gateway"])
        except ValueError as error:
            raise ValidationError("invalid_gateway", f"{location}.gateway", "Gateway harus alamat IPv4.") from error
        if gateway not in network or gateway in (network.network_address, network.broadcast_address):
            raise ValidationError("invalid_gateway", f"{location}.gateway", f"Gateway harus alamat host dalam subnet {network}, bukan network/broadcast.")
        ids.add(vlan["id"])
        names.add(vlan["name"])
        networks.append((vlan["id"], network))


def _validate_policy(data, inventory: dict, source: str):
    _object(data, {"schema_version", "default_action", "services", "rules"}, f"{source}:root")
    _version(data, source)
    if data["default_action"] != "deny":
        raise ValidationError("invalid_default_action", f"{source}:default_action", "Default action versi 1 harus deny.")
    services = data["services"]
    if not isinstance(services, dict) or not services:
        raise ValidationError("invalid_type", f"{source}:services", "Harus mapping layanan yang tidak kosong.")
    for name, terms in services.items():
        location = f"{source}:services.{name}"
        _string(name, f"{source}:services")
        _list(terms, location)
        pairs = set()
        for index, term in enumerate(terms):
            term_location = f"{location}[{index}]"
            _object(term, {"protocol", "destination_port"}, term_location)
            if term["protocol"] not in ("tcp", "udp"):
                raise ValidationError("invalid_protocol", f"{term_location}.protocol", "Protokol harus tcp atau udp.")
            _integer(term["destination_port"], 1, 65535, f"{term_location}.destination_port")
            pair = (term["protocol"], term["destination_port"])
            if pair in pairs:
                raise ValidationError("duplicate_service_term", term_location, "Pasangan protokol/port layanan duplikat.")
            pairs.add(pair)
    _list(data["rules"], f"{source}:rules", nonempty=False)
    vlan_ids = {vlan["id"] for vlan in inventory["vlans"]}
    rule_ids = set()
    for index, rule in enumerate(data["rules"]):
        location = f"{source}:rules[{index}]"
        _object(rule, {"id", "source_vlan", "destination_vlan", "service", "action"}, location)
        _string(rule["id"], f"{location}.id")
        if rule["id"] in rule_ids:
            raise ValidationError("duplicate_rule_id", f"{location}.id", f"ID aturan {rule['id']} sudah dipakai.")
        for field in ("source_vlan", "destination_vlan"):
            _integer(rule[field], 1, 4094, f"{location}.{field}")
            if rule[field] not in vlan_ids:
                raise ValidationError("unknown_vlan", f"{location}.{field}", f"VLAN {rule[field]} tidak ada dalam inventaris.")
        if rule["source_vlan"] == rule["destination_vlan"]:
            raise ValidationError("same_vlan", location, "VLAN sumber dan tujuan harus berbeda.")
        _string(rule["service"], f"{location}.service")
        if rule["service"] not in services:
            raise ValidationError("unknown_service", f"{location}.service", f"Layanan {rule['service']} tidak didefinisikan.")
        if rule["action"] not in ("allow", "deny"):
            raise ValidationError("invalid_action", f"{location}.action", "Tindakan harus allow atau deny.")
        rule_ids.add(rule["id"])


def load_inputs(policy_path: str | Path, inventory_path: str | Path) -> tuple[dict, dict]:
    """Kembalikan (policy, inventory) tervalidasi tanpa mengubah urutan atau data.

    Berhenti pada kesalahan pertama dengan ValidationError. Tidak menghasilkan
    atau menerapkan ACL, dan tidak menjalankan analisis konflik/shadowing.
    """
    inventory = _read_yaml(inventory_path)
    _validate_inventory(inventory, str(inventory_path))
    policy = _read_yaml(policy_path)
    _validate_policy(policy, inventory, str(policy_path))
    return policy, inventory
