import importlib.util
import pathlib
import sys
import types
import unittest


ansible_basic = types.ModuleType("ansible.module_utils.basic")
ansible_basic.AnsibleModule = object
sys.modules.setdefault("ansible", types.ModuleType("ansible"))
sys.modules.setdefault("ansible.module_utils", types.ModuleType("ansible.module_utils"))
sys.modules.setdefault("ansible.module_utils.basic", ansible_basic)

MODULE_PATH = pathlib.Path(__file__).parents[1] / "bigip_delete_node_pools.py"
SPEC = importlib.util.spec_from_file_location("bigip_delete_node_pools", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
F5NodeManager = MODULE.F5NodeManager


class Resource:
    def __init__(self, name, address=None):
        self.name = name
        self.address = address
        self.deleted = False

    def delete(self):
        self.deleted = True


class Collection:
    def __init__(self, values):
        self.values = values

    def get_collection(self):
        return self.values


class Pool(Resource):
    def __init__(self, name, members):
        super().__init__(name)
        self.members_s = Collection(members)


def root(nodes, pools):
    ltm = types.SimpleNamespace(nodes=Collection(nodes), pools=Collection(pools))
    return types.SimpleNamespace(tm=types.SimpleNamespace(ltm=ltm))


class F5NodeManagerTests(unittest.TestCase):
    def test_deletes_members_before_nodes_and_then_empty_pools(self):
        member = Resource("node-a:443", "192.0.2.10")
        node = Resource("node-a", "192.0.2.10")
        pool = Pool("application-443", [member])

        result = F5NodeManager(
            root([node], [pool]), ["192.0.2.10"],
            remove_port=True, delete_empty_pools=True,
        ).run()

        self.assertEqual(result["node_names"], ["node-a"])
        self.assertEqual(result["node_members"], ["node-a:443"])
        self.assertEqual(result["deleted_pools"], ["application"])
        self.assertTrue(result["changed"])
        self.assertTrue(member.deleted)
        self.assertTrue(node.deleted)
        self.assertTrue(pool.deleted)

    def test_keeps_pool_with_an_unmatched_member(self):
        target = Resource("target:443", "192.0.2.10")
        keeper = Resource("keeper:443", "192.0.2.20")
        pool = Pool("shared-443", [target, keeper])

        result = F5NodeManager(
            root([], [pool]), ["192.0.2.10"], delete_empty_pools=True
        ).run()

        self.assertEqual(result["deleted_pools"], [])
        self.assertFalse(pool.deleted)

    def test_check_mode_reports_without_deleting(self):
        member = Resource("node-a:80", "192.0.2.10")
        node = Resource("node-a", "192.0.2.10")
        pool = Pool("web-80", [member])

        result = F5NodeManager(
            root([node], [pool]), ["192.0.2.10"],
            delete_empty_pools=True, check_mode=True,
        ).run()

        self.assertTrue(result["changed"])
        self.assertEqual(result["deleted_pools"], ["web-80"])
        self.assertFalse(member.deleted)
        self.assertFalse(node.deleted)
        self.assertFalse(pool.deleted)

    def test_no_matches_is_idempotent(self):
        node = Resource("other", "192.0.2.20")
        result = F5NodeManager(root([node], []), ["192.0.2.10"]).run()
        self.assertEqual(result, {
            "changed": False,
            "node_names": [],
            "node_members": [],
            "deleted_pools": [],
        })


if __name__ == "__main__":
    unittest.main()
