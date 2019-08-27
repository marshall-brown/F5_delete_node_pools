#!/usr/bin/python
ANSIBLE_METADATA = {
    'metadata_version': '3.0',
    'status': ['development'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: bigip_delete_node_pools

short_description: "This module will delete nodes and delete any empty pools in the F5."

description:
    -   "This module will search through all the nodes based on a list of IPs ->
        and delete the node membership then delete the node. With the delete_emptypools ->
        flag set to true then the module will delete any empty pool in the F5.  

options:
    server:
        description:
            - What is the IP adddress of the F5
        required: true
    user:
        description:
            - Username to authenticate to the F5
        required: true
    password:
        description:
            - Password to authenticate to the F5
    ip:
        description:
            - List of IPs in question to delete nodes against
        Type: 
            - List    
    removeport:
        description:
            - Remove the trailing port
        Type:
            - Boolean    
    delete_emptypools:
        description: 
            - Delete any empty pool on the F5 System
        Type:
            - Boolean
author:
    - Marshall Brown (marshallb@vmware.com)
'''

EXAMPLES = '''
    # Delete using just a single IP  
    - name: Try to delete from IP
        bigip_delete_node_pools:
            server: SERVER
            user: USERNAME
            password: PASSWORD
            ip: 192.168.1.2
        delegate_to: localhost

    # Delete using list of IPs and remove trailing port as well as delete any empty F5 pool
    - name: Try to delete from IP
        bigip_delete_node_pools:
            server: SERVER
            user: USERNAME
            password: PASSWORD
            ip: lookup('dict', [192.168.2.1, 192.168.2.2, 192.168.2.3], wantlist=True)
            remove_port: True
            delete_emptypools: True
        delegate_to: localhost
'''

RETURN = '''
original_message:
    description: The original name param that was passed in
    type: str
message:
    description: The output message that the sample module generates
'''
from ansible.module_utils.basic import AnsibleModule
from ansibleutils import (
    create_results,
    return_results
)
import sys
sys.setrecursionlimit(5000)

try:
    from f5.bigip import ManagementRoot
    HAS_F5SDK = True
except ImportError:
    HAS_F5SDK = False

class F5Node(object):
    def __init__(self, params, results):
        self.server = params['server']
        self.username = params['user']
        self.password = params['password']
        self.ip = params['ip']
        self.remove_port = params['remove_port']
        self.result = results
        self.pools_with_node = []
        self.node_name = []
        self.delete_emptypools = params['delete_emptypools']
        mgmt = self.get_management_root_session()
        self.f5_nodes =  mgmt.tm.ltm.nodes.get_collection()
        self.f5_pools =  mgmt.tm.ltm.pools.get_collection()     

    def get_management_root_session(self):
        return ManagementRoot(
            self.server,
            self.username,
            self.password,
        )

    def deletenode(self):
        self.result['node_names'] = []
        for node in self.f5_nodes:
            if node.address in self.ip: 
                self.result['node_names'].append(node.name)
                #node.delete()
                self.result['changed'] = True
                self.result['success'] = True
            else:
                self.result['success'] = True
        return self.result

    def deleteemptypool(self):
        self.result['deleted_pools'] = []
        for pool in self.f5_pools:
            if pool.members_s.items:
                self.result['success'] = True
                continue                    
            else:
                if self.remove_port == True:
                    poolname = pool.name
                    noportpool = poolname.rsplit('-', 1)[0]
                    self.result['deleted_pools'].append(noportpool)
                else:
                    self.result['deleted_pools'].append(pool.name)
                self.result['changed'] = True
                self.result['success'] = True                    
                #pool.delete()    
        return self.result

    def deletemembership(self):
        self.result['node_member'] = []
        for pool_with_node in self.pools_with_node:
            for node_member in pool_with_node.members_s.get_collection():
                if node_member.name in self.node_name:
                    self.result['changed'] = True
                    self.result['success'] = True
                    self.result['node_member'].append(node_member.name)
                    #node_member.delete()
                else: self.result['success'] = True     
        return self.result

    def memberssearch(self):
        for pool in self.f5_pools: # Lets get the pools and the nodes/members that are apart of the pools
            for pool_member in pool.members_s.get_collection():
                if pool_member.address in self.ip:
                    self.pools_with_node.append(pool)
                    self.node_name.append(pool_member.name)
        return self.result                                                 

    def main(self):        
        result = self.result
        result = self.memberssearch()
        result = self.deletemembership()
        result = self.deletenode()
        if self.delete_emptypools is True:
            result = self.deleteemptypool()
        return result

def _set_failed(result, msg):
    result['msg'] = msg
    result['success'] = False
    return result        

def main():    
    module = AnsibleModule(
        argument_spec=dict(
            server=dict(required=True, type='str'),
            user=dict(required=True, type='str', aliases=['username']),
            password=dict(required=True, type='str', no_log=True),
            provider=dict(required=False, type='dict'),
            ip=dict(required=True, type='str'),
            remove_port=dict(required=False, type='bool', default='False'),
            delete_emptypools=dict(required=False, type='bool', default='False')
            ),        
        supports_check_mode=False
    )

    if not HAS_F5SDK:
        module.fail_json(msg="The python f5-sdk module is required")

    if not module.check_mode:
        results = create_results(module.params)
        results = F5Node(module.params, results).main()
        return_results(module, results)

if __name__ == '__main__':
    main()