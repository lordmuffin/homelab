"""A Python Pulumi program"""
import os, yaml, random, string
import pulumi
from pulumi import Output
import pulumi_proxmoxve as proxmox
from pulumi_command import local, remote
import pulumiverse_time as time
import files.vm as vm
import files.vm_bootstrap as bootstrap

# from dotenv import load_dotenv
import ipaddress

providers_path = "../config/providers/"
folder_path = "../config/dev-kairos-lab/"

def random_char(length):
    chars = string.digits + string.ascii_letters
    random_char = ''.join(random.sample(chars, length))
    return random_char

def load_folders_from_path(folder_path):
    filenames= os.listdir (".") # get all files' and folders' names in the current directory

    result = []
    for filename in filenames: # loop through all the files and folders
        if os.path.isdir(os.path.join(os.path.abspath("."), filename)): # check whether the current object is a folder or not
            result.append(filename)

    result.sort()
    print(result)

    return result

def load_yaml_files_from_folder(folder_path):
    yaml_files = [file for file in os.listdir(folder_path) if file.endswith(".yaml")]
    yaml_files = sorted(yaml_files)
    loaded_data = []

    for yaml_file in yaml_files:
        file_path = os.path.join(folder_path, yaml_file)
        with open(file_path, 'r') as file:
            yaml_data = yaml.safe_load(file)
            loaded_data.append(yaml_data)

    return loaded_data

def vm_virtual_machine(i, name, node_name, hostpcis, provider, depends_on, ignore_changes):
    base_vm_id=i['vm_id'],

    for disk_entry in i['disks']:
        for d in disk_entry:
            disks.append(
                proxmox.vm.VirtualMachineDiskArgs(
                    interface=disk_entry[d]['interface'],
                    datastore_id=disk_entry[d]['datastore_id'],
                    size=disk_entry[d]['size'],
                    file_format=disk_entry[d]['file_format'],
                    cache=disk_entry[d]['cache']
                )
            )

    for net_entry in i['network_devices']:
        for n in net_entry:
            print(f"NETWORK INTERFACES:: {n}")
            nets.append(
                proxmox.vm.VirtualMachineNetworkDeviceArgs(
                    bridge=net_entry[n]['bridge'],
                    model=net_entry[n]['model'],
                    vlan_id=net_entry[n]['vlan_id']
                )
            )

    for disk_entry in i['disks']:
        for d in disk_entry:
            disks.append(
                proxmox.vm.VirtualMachineDiskArgs(
                    interface=disk_entry[d]['interface'],
                    datastore_id=disk_entry[d]['datastore_id'],
                    size=disk_entry[d]['size'],
                    file_format=disk_entry[d]['file_format'],
                    cache=disk_entry[d]['cache']
                )
            )
    
    agent = proxmox.vm.VirtualMachineAgentArgs(
                        enabled=i['agent']['enabled'],
                        # trim=v['agent']['trim'],
                        type=i['agent']['type']
                    )
    cpu=proxmox.vm.VirtualMachineCpuArgs(
                        cores=i['cpu']['cores'],
                        sockets=i['cpu']['sockets'],
                        type="x86-64-v2-AES"
                    )
    memory=proxmox.vm.VirtualMachineMemoryArgs(
                        dedicated=i['memory']['dedicated']
                    )
    
    # For Mappings hostpci
    # Need to fix a problem for using GPU across multiple environments.
    if hostpcis != "" and i['vm_type'] == "gpu-agent":
        hostpcis_map = proxmox.vm.VirtualMachineHostpciArgs(
            device="hostpci0",
            mapping=hostpcis
        )

        vm = proxmox.vm.VirtualMachine(
            vm_id=base_vm_id[0],
            resource_name=name,
            node_name=node_name,
            agent=agent,
            bios=i['bios'],
            cpu=cpu,
            disks=disks,
            memory=memory,
            name=name,
            network_devices=nets,
            hostpcis=[hostpcis_map],
            on_boot=i['on_boot'],
            opts=pulumi.ResourceOptions(provider=provider,ignore_changes=ignore_changes, depends_on=depends_on)
        )

    else:
        vm = proxmox.vm.VirtualMachine(
            vm_id=base_vm_id[0],
            resource_name=name,
            node_name=node_name,
            agent=agent,
            bios=i['bios'],
            cpu=cpu,
            disks=disks,
            memory=memory,
            name=name,
            network_devices=nets,
            on_boot=i['on_boot'],
            opts=pulumi.ResourceOptions(provider=provider,ignore_changes=ignore_changes, depends_on=depends_on)
        )

    name = name
    dial_error_limit = 25
    per_dial_timeout = 30

    environments = ["dev", "prod"]
    primary_server_ip = [{
        "environment": "dev",
        "ip": "192.168.10.30",
    },
    {
        "environment": "prod",
        "ip": "192.168.11.30",
    }]

    # for ip_config_entry in v['cloud_init']['ip_configs']:
    #     ipv4 = ip_config_entry.get('ipv4')
    #     ip, subnet = ipv4.get('address', '').split('/')
    #     gateway = ipv4.get('gateway')

    # for env in environments:
    #     if env == i["environment"]:
    #         for env in primary_server_ip:
    #             if env["environment"] == i["environment"]:
    #                 server_ip = env["ip"]

    return vm



# Gather Data
providers_data = load_yaml_files_from_folder(providers_path)
dev_cluster_path = load_yaml_files_from_folder(folder_path)
# prod_cluster_path = "../config/prod-kairos-lab/"

# Build Providers
providers = []
for p in providers_data:
    for i in p:
        provider = proxmox.Provider(i["name"],
                        endpoint=i["endpoint"],
                        insecure=i["insecure"],
                        username=i["username"],
                        password=os.getenv("PROXMOX_VE_PASSWORD"),
                        )
        
        tmp_p = {}
        tmp_p["name"] = i["name"]
        tmp_p["node_name"] = i["node_name"]
        tmp_p["hostpcis"] = i["hostpcis"]
        tmp_p["provider"] = provider

        providers.append(tmp_p)

agent_depends_on = []
# pause = time.Sleep(f"wait30Seconds-pre-server-create", create_duration="30s", opts=pulumi.ResourceOptions())
# agent_depends_on.append(pause)

for servers in dev_cluster_path:
    # dev-lab cluster Server builds
    disks = []
    nets = []
    ip_configs = []
    ssh_keys = []
    vm_ids = []
    public_ip_addresses = [] # create an array to store the information
    dependencies = []
    server_vms = [] 
    depends_on = []

    for v in servers:
        # base_resource_name=v['environment'] + "-" + v['resource_name'] + "-" + v['vm_type']
        name = v["environment"] + "-" + v["resource_name"] + "-" + v["vm_type"] + "-" + v["suffix"]
        # name = f"{v['environment']}-{v['resource_name']}-{v['vm_type']}-{v['suffix']}"

        for p in providers:
            if p["node_name"] == v["node_name"]:
                current_provider = p["provider"]

                virtual_machine = vm_virtual_machine(
                    i=v,
                    name=name,
                    node_name=v["node_name"],
                    hostpcis=p["hostpcis"],
                    provider=current_provider,
                    depends_on=None,
                    ignore_changes=v['ignore_changes'],
                )
                agent_depends_on.append(virtual_machine) #ERROR - This is not getting item before next loop starts.
