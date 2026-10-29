import unittest

from drift_detection.parsers import (
    extract_json,
    normalize_interfaces,
    normalize_operational_routes,
    parse_running_config,
)


class ParserTests(unittest.TestCase):
    def test_json_extractor_ignores_vtysh_warning(self):
        self.assertEqual(extract_json("% warning\n{\"eth1\": {\"mtu\": 1500}}"), {"eth1": {"mtu": 1500}})

    def test_interface_normalization_sorts_ipv4_and_separates_oper_state(self):
        parsed = normalize_interfaces(
            {
                "eth1": {
                    "administrativeStatus": "up",
                    "operationalStatus": "down",
                    "mtu": 1500,
                    "ipAddresses": [
                        {"address": "2001:db8::1/64"},
                        {"address": "10.0.0.1/30"},
                    ],
                }
            }
        )
        self.assertEqual(parsed["eth1"], {"addresses": ["10.0.0.1/30"], "admin_up": True, "oper_up": False, "mtu": 1500})

    def test_operational_route_order_is_normalized(self):
        parsed = normalize_operational_routes(
            {
                "10.0.0.0/24": [
                    {
                        "prefix": "10.0.0.0/24",
                        "protocol": "ospf",
                        "selected": True,
                        "installed": True,
                        "nexthops": [
                            {"ip": "10.0.0.3", "interfaceName": "eth2"},
                            {"ip": "10.0.0.2", "interfaceName": "eth1"},
                        ],
                    }
                ]
            }
        )
        self.assertEqual(parsed[0]["next_hops"][0]["ip"], "10.0.0.2")

    def test_running_config_extracts_static_and_ospf_config(self):
        parsed = parse_running_config(
            """Building configuration...
Current configuration:
ip route 203.0.113.0/24 10.0.0.2 5
router ospf
 ospf router-id 10.255.0.1
 passive-interface lo
 network 10.0.0.0/255.255.255.252 area 0.0.0.0
!
"""
        )
        self.assertEqual(parsed["static_routes"], [{"prefix": "203.0.113.0/24", "next_hop": "10.0.0.2", "distance": 5}])
        self.assertEqual(parsed["ospf"]["router_id"], "10.255.0.1")
        self.assertEqual(parsed["ospf"]["networks"], [{"prefix": "10.0.0.0/30", "area": "0.0.0.0"}])
        self.assertEqual(parsed["ospf"]["passive_interfaces"], ["lo"])


if __name__ == "__main__":
    unittest.main()
