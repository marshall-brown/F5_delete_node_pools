# BIG-IP node and pool cleanup

An Ansible module that safely removes BIG-IP nodes in dependency order:

1. Delete pool memberships whose address matches one of the requested IPs.
2. Delete the matching nodes.
3. Optionally delete pools that are empty after those memberships are removed.

The module supports Ansible check mode, so a cleanup can be previewed without
changing the appliance.

## Requirements

- Python 3.8 or newer
- Ansible Core
- [`f5-sdk`](https://pypi.org/project/f5-sdk/) on the Ansible controller

## Usage

Place `bigip_delete_node_pools.py` in a `library/` directory next to the
playbook, then call it as follows:

```yaml
- name: Remove retired BIG-IP nodes and newly empty pools
  bigip_delete_node_pools:
    server: bigip.example.com
    user: admin
    password: "{{ vault_bigip_password }}"
    ip:
      - 192.0.2.10
      - 192.0.2.11
    delete_emptypools: true
  delegate_to: localhost
```

Run the playbook with `--check` to preview the affected memberships, nodes,
and pools. Pool deletion considers the post-cleanup state even in check mode.

> **Warning:** `delete_emptypools: true` removes every empty pool visible on
> the BIG-IP, not only pools that contained one of the selected nodes.
