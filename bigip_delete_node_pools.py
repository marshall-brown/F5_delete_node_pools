#!/usr/bin/python
"""Remove BIG-IP nodes, their pool memberships, and optionally empty pools."""

from importlib import import_module

from ansible.module_utils.basic import AnsibleModule


DOCUMENTATION = r"""
---
module: bigip_delete_node_pools
short_description: Remove nodes and optionally delete empty pools from BIG-IP
description:
  - Removes memberships for nodes matching the supplied IP addresses.
  - Removes the matching nodes after their memberships are gone.
  - Can also remove every empty pool.
options:
  server:
    description: BIG-IP management address.
    type: str
    required: true
  user:
    description: Username used to authenticate to BIG-IP.
    type: str
    required: true
  password:
    description: Password used to authenticate to BIG-IP.
    type: str
    required: true
  ip:
    description: IP address or addresses of nodes to remove.
    type: list
    elements: str
    required: true
  remove_port:
    description: Remove the final hyphen-delimited suffix from pool names in the result.
    type: bool
    default: false
  delete_emptypools:
    description: Remove all pools that have no members after node removal.
    type: bool
    default: false
author:
  - Marshall Brown (@marshallb)
"""

EXAMPLES = r"""
- name: Delete nodes by address
  bigip_delete_node_pools:
    server: bigip.example.com
    user: admin
    password: "{{ bigip_password }}"
    ip:
      - 192.0.2.10
      - 192.0.2.11

- name: Preview node and empty-pool deletion
  bigip_delete_node_pools:
    server: bigip.example.com
    user: admin
    password: "{{ bigip_password }}"
    ip: 192.0.2.10
    delete_emptypools: true
  check_mode: true
"""

RETURN = r"""
node_names:
  description: Names of matching nodes.
  returned: always
  type: list
  elements: str
node_members:
  description: Names of matching pool members.
  returned: always
  type: list
  elements: str
deleted_pools:
  description: Names of empty pools selected for deletion.
  returned: always
  type: list
  elements: str
"""


class F5NodeManager:
    """Perform node cleanup against an f5-sdk management root."""

    def __init__(self, management_root, addresses, remove_port=False,
                 delete_empty_pools=False, check_mode=False):
        self.ltm = management_root.tm.ltm
        self.addresses = set(addresses)
        self.remove_port = remove_port
        self.delete_empty_pools = delete_empty_pools
        self.check_mode = check_mode

    def run(self):
        """Apply the cleanup in dependency order and return Ansible results."""
        pools = list(self.ltm.pools.get_collection())
        nodes = [
            node for node in self.ltm.nodes.get_collection()
            if node.address in self.addresses
        ]
        node_members = []

        for pool in pools:
            for member in list(pool.members_s.get_collection()):
                if member.address in self.addresses:
                    node_members.append(member.name)
                    if not self.check_mode:
                        member.delete()

        for node in nodes:
            if not self.check_mode:
                node.delete()

        deleted_pools = []
        if self.delete_empty_pools:
            for pool in pools:
                members = list(pool.members_s.get_collection())
                # In check mode matching members still exist remotely, so model
                # the state that would remain after this module removes them.
                remaining = [m for m in members if m.address not in self.addresses]
                if not remaining:
                    deleted_pools.append(self._display_pool_name(pool.name))
                    if not self.check_mode:
                        pool.delete()

        return {
            "changed": bool(node_members or nodes or deleted_pools),
            "node_names": [node.name for node in nodes],
            "node_members": node_members,
            "deleted_pools": deleted_pools,
        }

    def _display_pool_name(self, name):
        if self.remove_port and "-" in name:
            return name.rsplit("-", 1)[0]
        return name


def create_management_root(server, user, password):
    """Load the optional SDK only when the module actually runs."""
    management_root = import_module("f5.bigip").ManagementRoot
    return management_root(server, user, password)


def main():
    module = AnsibleModule(
        argument_spec={
            "server": {"required": True, "type": "str"},
            "user": {"required": True, "type": "str", "aliases": ["username"]},
            "password": {"required": True, "type": "str", "no_log": True},
            "ip": {"required": True, "type": "list", "elements": "str"},
            "remove_port": {"type": "bool", "default": False},
            "delete_emptypools": {"type": "bool", "default": False},
        },
        supports_check_mode=True,
    )

    try:
        root = create_management_root(
            module.params["server"], module.params["user"], module.params["password"]
        )
        result = F5NodeManager(
            root,
            module.params["ip"],
            remove_port=module.params["remove_port"],
            delete_empty_pools=module.params["delete_emptypools"],
            check_mode=module.check_mode,
        ).run()
    except (ImportError, ModuleNotFoundError):
        module.fail_json(msg="The Python f5-sdk package is required")
    except Exception as exc:
        module.fail_json(msg="BIG-IP node cleanup failed: {0}".format(exc))

    module.exit_json(**result)


if __name__ == "__main__":
    main()
