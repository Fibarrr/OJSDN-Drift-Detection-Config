import unittest

from drift_detection.detector import detect_drift


def fixture():
    baseline = {
        "management_interface": "eth0",
        "ospf": {"area": "0.0.0.0", "passive_interfaces": ["lo"]},
        "routers": {
            "r1": {
                "router_id": "10.255.0.1",
                "interfaces": {
                    "lo": {"addresses": ["10.255.0.1/32"], "admin_up": True, "mtu": 65536},
                    "eth1": {"addresses": ["10.0.12.1/30"], "admin_up": True, "mtu": 9500},
                },
                "static_routes": [],
                "ospf": {"networks": ["10.0.12.0/30", "10.255.0.1/32"]},
            }
        },
    }
    router = {
        "configuration": {
            "interfaces": {
                "eth0": {"addresses": ["172.20.20.3/24"], "admin_up": True, "mtu": 1500},
                "eth1": {"addresses": ["10.0.12.1/30"], "admin_up": True, "mtu": 9500},
                "lo": {"addresses": ["10.255.0.1/32"], "admin_up": True, "mtu": 65536},
            },
            "static_routes": [],
            "ospf": {
                "router_id": "10.255.0.1",
                "networks": [
                    {"prefix": "10.255.0.1/32", "area": "0.0.0.0"},
                    {"prefix": "10.0.12.0/30", "area": "0.0.0.0"},
                ],
                "passive_interfaces": ["lo"],
            },
        },
        "operational": {"routing_table": []},
    }
    return baseline, {"routers": {"r1": router}}


class GraphDetectorTests(unittest.TestCase):
    def test_same_semantics_ignore_order_and_dynamic_route_table(self):
        baseline, observed = fixture()
        observed["routers"]["r1"]["operational"]["routing_table"] = [
            {"prefix": "10.0.12.0/30", "protocol": "ospf", "next_hops": []}
        ]
        self.assertEqual(detect_drift(baseline, observed), [])

    def test_mtu_change_is_detected(self):
        baseline, observed = fixture()
        observed["routers"]["r1"]["configuration"]["interfaces"]["eth1"]["mtu"] = 9000
        drift = detect_drift(baseline, observed)
        self.assertTrue(any(item.get("attribute") == "mtu" for item in drift))

    def test_interface_address_change_is_detected(self):
        baseline, observed = fixture()
        observed["routers"]["r1"]["configuration"]["interfaces"]["eth1"]["addresses"] = ["10.0.12.5/30"]
        drift = detect_drift(baseline, observed)
        self.assertTrue(any(item.get("attribute") == "addresses" for item in drift))

    def test_static_route_addition_is_detected(self):
        baseline, observed = fixture()
        observed["routers"]["r1"]["configuration"]["static_routes"] = [
            {"prefix": "203.0.113.0/24", "next_hop": "10.0.12.2", "distance": 1}
        ]
        drift = detect_drift(baseline, observed)
        self.assertTrue(any("static-route/r1/203.0.113.0/24" in item.get("object", "") for item in drift))

    def test_static_route_deletion_is_detected(self):
        baseline, observed = fixture()
        route = {"prefix": "203.0.113.0/24", "next_hop": "10.0.12.2", "distance": 1}
        baseline["routers"]["r1"]["static_routes"] = [route]
        drift = detect_drift(baseline, observed)
        self.assertTrue(any(item.get("kind") == "missing_object" and "static-route/r1/203.0.113.0/24" in item.get("object", "") for item in drift))


if __name__ == "__main__":
    unittest.main()
