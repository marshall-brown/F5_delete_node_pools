from f5.bigip import ManagementRoot
import sys
import time

sys.setrecursionlimit(5000) # Allow python to recurse more than the default 999. There are over 4000 Pools we need to iterate through :(

# Connect to the BigIP and configure the basic objects
mgmt = ManagementRoot('', '', '')
ltm = mgmt.tm.ltm
ip = [""]
pool_members = []
pool_name = []
pools = []
print("Starting node")
f5_nodes = mgmt.tm.ltm.nodes.get_collection()
print("finish node")
print("starting pool")
f5_pools = mgmt.tm.ltm.pools.get_collection()
print("finish pool")

def deletenode():
    for node in f5_nodes:
        if node.address in ip:
            print(ip)
            print("Inside Deletenode func " + node.address)
            node.delete()
            print("Deleting")# why is it not reading this

def deletepool():
    for pool in f5_pools:
        if pool.name in pool_name: # iterate through the pool list. If the pool 
            print("inside deletepool")
            print(pool.name)
            print(pool_name)
            print("Inside deletepool func")
            print(pool)
            pool.delete()

print("starting members search")
for pool in f5_pools: # Lets get the pools and the nodes/members that are apart of the pools
    for pool_member in pool.members_s.get_collection():
        if pool_member.address in ip:
            print("pool member name = " + pool_member.name)
            print("pool name = " + pool.name)
            pool_members.append(pool_member.name)
            pool_name.append(pool.name)
            pools.append(pool)

def main():
    start = time.time()
    deletepool()
    deletenode()
    end = time.time()
    print( end - start)

if __name__ == '__main__':
    main()    

# for node in f5_nodes:
#     if node.address in ip:  
#         print("Initial Pool Delete")
#         deletepool()