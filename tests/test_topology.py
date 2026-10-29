"""Periksa konsistensi jalur VLAN dengan inventaris tanpa menjalankan container."""

from ipaddress import IPv4Interface, IPv4Network
from pathlib import Path
import re
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]


class TopologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = yaml.safe_load(
            (ROOT / "topology/vlans.yaml").read_text(encoding="utf-8")
        )["vlans"]
        cls.topology = yaml.safe_load(
            (ROOT / "topology/campus.clab.yml").read_text(encoding="utf-8")
        )["topology"]
        cls.nodes = cls.topology["nodes"]
        cls.peers = {}
        for link in cls.topology["links"]:
            left, right = link["endpoints"]
            for endpoint, peer in ((left, right), (right, left)):
                if endpoint in cls.peers:
                    raise AssertionError(f"Interface dipakai dua link: {endpoint}")
                cls.peers[endpoint] = peer

    def test_links_use_data_interfaces_and_existing_nodes(self):
        for endpoint in self.peers:
            node, interface = endpoint.split(":")
            self.assertIn(node, self.nodes)
            self.assertRegex(interface, r"^eth[1-9][0-9]*$")

    def test_each_vlan_has_an_access_trunk_gateway_and_host_route(self):
        router = self.nodes["router"]["exec"]
        switch = self.nodes["switch"]["exec"]
        router_port = self.peers["switch:eth1"]
        self.assertEqual(router_port, "router:eth1")
        self.assertIn(
            "ip link add name br0 type bridge vlan_filtering 1 vlan_default_pvid 0",
            switch,
        )
        self.assertEqual(
            set(self.nodes),
            {"router", "switch"} | {v["name"].lower() for v in self.inventory},
        )
        for vlan in self.inventory:
            with self.subTest(vlan=vlan["id"]):
                host = vlan["name"].lower()
                commands = self.nodes[host]["exec"]
                addresses = [
                    re.fullmatch(r"ip address replace (\S+) dev eth1", command)
                    for command in commands
                ]
                addresses = [match[1] for match in addresses if match]
                self.assertEqual(len(addresses), 1)
                address = IPv4Interface(addresses[0])
                network = IPv4Network(vlan["subnet"])
                self.assertEqual(address.network, network)
                self.assertNotIn(
                    str(address.ip),
                    (vlan["gateway"], str(network.network_address),
                     str(network.broadcast_address)),
                )
                self.assertIn("ip link set dev eth1 up", commands)
                self.assertIn(
                    f"ip route replace default via {vlan['gateway']} dev eth1",
                    commands,
                )
                peer_node, access_port = self.peers[f"{host}:eth1"].split(":")
                self.assertEqual(peer_node, "switch")
                self.assertIn(f"ip link set dev {access_port} master br0", switch)
                self.assertIn(f"ip link set dev {access_port} up", switch)
                self.assertIn(
                    f"bridge vlan add dev {access_port} vid {vlan['id']} pvid untagged",
                    switch,
                )
                self.assertIn(f"bridge vlan add dev eth1 vid {vlan['id']}", switch)
                subinterface = f"eth1.{vlan['id']}"
                self.assertIn(
                    f"ip link add link eth1 name {subinterface} type vlan id {vlan['id']}",
                    router,
                )
                self.assertIn(
                    f"ip address replace {vlan['gateway']}/{network.prefixlen} dev {subinterface}",
                    router,
                )
                self.assertIn(f"ip link set dev {subinterface} up", router)
        self.assertIn("ip link set dev eth1 master br0", switch)
        self.assertIn("ip link set dev eth1 up", switch)
        self.assertIn("ip link set dev eth1 up", router)

    def test_only_router_forwards_and_startup_does_not_apply_acl(self):
        defaults = self.topology["defaults"]
        self.assertEqual(defaults["image"], "campus-acl-router:1.0")
        self.assertEqual(defaults["image-pull-policy"], "Never")
        for name, node in self.nodes.items():
            sysctls = defaults["sysctls"] | node.get("sysctls", {})
            self.assertEqual(sysctls["net.ipv4.ip_forward"], "1" if name == "router" else "0")
            for command in node["exec"]:
                self.assertNotRegex(command, r"\b(nft|iptables|ip6tables)\b")


if __name__ == "__main__":
    unittest.main()
