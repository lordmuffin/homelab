"""A Python Pulumi program"""
import os
import pulumi
from pulumi import Output
import pulumi_proxmoxve as proxmoxve
from pulumi_command import local, remote
import pulumiverse_time as time
import files.vm as vm
import files.vm_bootstrap as bootstrap


# Variables

# Providers
# node_pve_router_provider = proxmoxve.Provider('node_pve_router_provider',
#     endpoint="https://192.168.1.11:8006/",
#     username=os.getenv("PROXMOX_VE_USERNAME"),
#     password=os.getenv("PROXMOX_VE_PASSWORD"),
#     insecure=True
# )
# node_pve_provider = proxmoxve.Provider('node_pve_provider',
#     endpoint="https://192.168.1.13:8006/",
#     username=os.getenv("PROXMOX_VE_USERNAME"),
#     password=os.getenv("PROXMOX_VE_PASSWORD"),
#     insecure=True
# )
# node_pve2_provider = proxmoxve.Provider('node_pve2_provider',
#     endpoint="https://192.168.1.14:8006/",
#     username=os.getenv("PROXMOX_VE_USERNAME"),
#     password=os.getenv("PROXMOX_VE_PASSWORD"),
#     insecure=True
# )
# node_pve_nas_01_provider = proxmoxve.Provider('node_pve_nas_01_provider',
#     endpoint="https://192.168.1.15:8006/",
#     username=os.getenv("PROXMOX_VE_USERNAME"),
#     password=os.getenv("PROXMOX_VE_PASSWORD"),
#     insecure=True
# )

# providers = [node_pve_provider, node_pve2_provider, node_pve_nas_01_provider]
# control_node_config_list = [
#     {
#         "node_name": "pve",
#         "provider": node_pve_provider,
#         "image_id": 104,
#         "description": "Ubuntu 22.04 v1.0.7 :: K3s w/Cilium & Kube-VIP",
#         "on_boot": True,
#         "reboot": False,
#         "started": False,
#         "ip": "192.168.10.20/24",
#         "ssh_pub_keys": ["ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEGoIpTIeC7Kby3lHyw2g2kTwkb3MHCDPCJKzHWa6uhe"]
#     },
#     {
#         "node_name": "pve2",
#         "provider": node_pve2_provider,
#         "image_id": 102,
#         "description": "Ubuntu 22.04 v1.0.7 :: K3s w/Cilium & Kube-VIP",
#         "on_boot": True,
#         "reboot": False,
#         "started": False,
#         "ip": "192.168.10.21/24",
#         "ssh_pub_keys": ["ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEGoIpTIeC7Kby3lHyw2g2kTwkb3MHCDPCJKzHWa6uhe"]
#     },
#     {
#         "node_name": "pve-nas-01",
#         "provider": node_pve_nas_01_provider,
#         "image_id": 115,
#         "description": "Ubuntu 22.04 v1.0.7 :: K3s w/Cilium & Kube-VIP",
#         "on_boot": True,
#         "reboot": False,
#         "started": False,
#         "ip": "192.168.10.22/24",
#         "ssh_pub_keys": ["ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEGoIpTIeC7Kby3lHyw2g2kTwkb3MHCDPCJKzHWa6uhe"]
#     }
# ]
# control_node_ip_list = [
#     {
#         "name": "dev-k3s-lab-001",
#         "ip": "192.168.10.91",
#         "ssh_key": ""
#     },
#     {
#         "name": "dev-k3s-lab-002",
#         "ip": "192.168.10.95",
#         "ssh_key": ""
#     },
#     {
#         "name": "dev-k3s-lab-003",
#         "ip": "192.168.10.93",
#         "ssh_key": ""
#     }
# ]
# control_vms = vm.ubuntu_k3s_control_node(control_node_config_list)

# control_vms_bootstrap = bootstrap.bootstrap(control_node_ip_list)


import pulumi
import pulumi_proxmoxve as proxmox
import os,yaml
# from dotenv import load_dotenv
import ipaddress
import files.vm_bootstrap as bootstrap

# load_dotenv()
# provider = proxmox.Provider('proxmoxve',
#                             endpoint=os.getenv("PROXMOX_ENDPOINT"),
#                             insecure=os.getenv("PROXMOX_INSECURE"),
#                             username=os.getenv("PROXMOX_USERNAME"),
#                             password=os.getenv("PROXMOX_PASSWORD"),
#                             )
providers_path = "../config/providers/"
folder_path = "../config/vms/"

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
    loaded_data = []

    for yaml_file in yaml_files:
        file_path = os.path.join(folder_path, yaml_file)
        with open(file_path, 'r') as file:
            yaml_data = yaml.safe_load(file)
            loaded_data.append(yaml_data)

    return loaded_data

def get_server_ip(parsed_data, env):
    server_ip = "" # Set here to reset server ip per yaml file.
    for vm in parsed_data:
        for v in vm:
            if v["environment"] == env:
                # Set server_ip for first time.
                if v["vm_type"] == "server":
                    for ip_config_entry in v['cloud_init']['ip_configs']:
                        ipv4 = ip_config_entry.get('ipv4')

                        if ipv4:
                            new_address = ''
                            ip, subnet = ipv4.get('address', '').split('/')
                            server_ip = ip
            
    return server_ip


# environments = load_folders_from_path(folder_path)
parsed_data = load_yaml_files_from_folder(folder_path)
providers_data = load_yaml_files_from_folder(providers_path)

providers = []

for p in providers_data:
    for i in p:
        providers_i = {}
        provider = proxmox.Provider(i["name"],
                        endpoint=i["endpoint"],
                        insecure=i["insecure"],
                        username=i["username"],
                        password=os.getenv("PROXMOX_VE_PASSWORD"),
                        )

        providers_i["name"] = i["name"]
        providers_i["node_name"] = i["node_name"]
        providers_i["provider"] = provider
        providers_i["hostpcis"] = i["hostpcis"]

        providers.append(providers_i)

for vm in parsed_data:
    disks = []
    nets = []
    ip_configs = []
    ssh_keys = []
    vm_ids = []
    public_ip_addresses = [] # create an array to store the information
    dependencies = []

    for v in vm:
        if v["vm_type"] == "server":
            for vmcount in range(v['count']):
                base_resource_name=v['environment'] + "-" + v['resource_name'] + "-" + v['vm_type']
                name_counter = vmcount + 1
                base_vm_id=v['vm_id'],

                provider = providers[vmcount]["provider"]
                node_name = providers[vmcount]["node_name"]

                for disk_entry in v['disks']:
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

                for ip_config_entry in v['cloud_init']['ip_configs']:
                    ipv4 = ip_config_entry.get('ipv4')

                    if ipv4:
                        new_address = ''
                        ip, subnet = ipv4.get('address', '').split('/')
                        gateway = ipv4.get('gateway')
                        new_ip = str(ipaddress.ip_address(ip) + vmcount)
                        new_address = f"{new_ip}/{subnet}"

                        ip_configs = []
                        ip_configs.append(
                            proxmox.vm.VirtualMachineInitializationIpConfigArgs(
                                ipv4=proxmox.vm.VirtualMachineInitializationIpConfigIpv4Args(
                                    address=new_address,
                                    gateway=gateway
                                )
                            )
                        )

                for ssk_keys_entry in v['cloud_init']['user_account']['keys']:
                    ssh_keys.append(ssk_keys_entry)

                if os.getenv("SSH_PUB_KEY"):
                    ssh_keys.append(os.getenv("SSH_PUB_KEY"))

                for net_entry in v['network_devices']:
                    for n in net_entry:
                        print(f"NETWORK INTERFACES:: {n}")
                        nets.append(
                            proxmox.vm.VirtualMachineNetworkDeviceArgs(
                                bridge=net_entry[n]['bridge'],
                                model=net_entry[n]['model'],
                                vlan_id=net_entry[n]['vlan_id']
                            )
                        )

                virtual_machine = proxmox.vm.VirtualMachine(
                    vm_id=base_vm_id[0] + vmcount,
                    resource_name=f"{base_resource_name}-{name_counter:03d}",
                    node_name=node_name,
                    agent=proxmox.vm.VirtualMachineAgentArgs(
                        enabled=v['agent']['enabled'],
                        # trim=v['agent']['trim'],
                        type=v['agent']['type']
                    ),
                    bios=v['bios'],
                    cpu=proxmox.vm.VirtualMachineCpuArgs(
                        cores=v['cpu']['cores'],
                        sockets=v['cpu']['sockets'],
                        type="kvm64"
                    ),
                    clone=proxmox.vm.VirtualMachineCloneArgs(
                        node_name=node_name,
                        vm_id=v["clone_vm_id"],
                        full=v['clone']['full'],
                    ),
                    disks=disks,
                    memory=proxmox.vm.VirtualMachineMemoryArgs(
                        dedicated=v['memory']['dedicated']
                    ),
                    name=f"{base_resource_name}-{name_counter:03d}",
                    network_devices=nets,
                    initialization=proxmox.vm.VirtualMachineInitializationArgs(
                        type=v['cloud_init']['type'],
                        datastore_id=v['cloud_init']['datastore_id'],
                        interface=v['cloud_init']['interface'],
                        dns=proxmox.vm.VirtualMachineInitializationDnsArgs(
                            domain=v['cloud_init']['dns']['domain'],
                            servers=v['cloud_init']['dns']['servers']
                        ),
                        ip_configs=ip_configs,
                        user_account=proxmox.vm.VirtualMachineInitializationUserAccountArgs(
                            username=v['cloud_init']['user_account']['username'],
                            password=v['cloud_init']['user_account']['password'],
                            keys=ssh_keys
                        ),
                    ),
                    on_boot=v['on_boot'],
                    reboot=v['on_boot'],
                    opts=pulumi.ResourceOptions(provider=provider,ignore_changes=v['ignore_changes']),
                )

                vm_details = Output.all(virtual_machine.name, virtual_machine.id) \
                .apply(lambda args: {
                    args[0]: args[1]
                })
                # vm_id = virtual_machine.id.apply(lambda id: virtual_machine.id)
                # vm_name = f"{base_resource_name}-{name_counter}",
                vm_ids.append(vm_details)

                # wait30_seconds = time.Sleep(f"wait30Seconds-{base_resource_name}-{name_counter:03d}-build", create_duration="30s", opts=pulumi.ResourceOptions(depends_on=[virtual_machine]))

                # dependencies.append(wait30_seconds)
                dependencies.append(virtual_machine)

                pulumi.export(v['name'], virtual_machine.id)

        elif v["vm_type"] == "agent":
            for vmcount in range(v['count']):
                base_resource_name=v['environment'] + "-" + v['resource_name'] + "-" + v['vm_type']
                name_counter = vmcount + 1
                base_vm_id=v['vm_id'],

                provider = providers[vmcount]["provider"]
                node_name = providers[vmcount]["node_name"]

                for disk_entry in v['disks']:
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

                for ip_config_entry in v['cloud_init']['ip_configs']:
                    ipv4 = ip_config_entry.get('ipv4')

                    if ipv4:
                        new_address = ''
                        ip, subnet = ipv4.get('address', '').split('/')
                        gateway = ipv4.get('gateway')
                        new_ip = str(ipaddress.ip_address(ip) + vmcount)
                        new_address = f"{new_ip}/{subnet}"

                        ip_configs = []
                        ip_configs.append(
                            proxmox.vm.VirtualMachineInitializationIpConfigArgs(
                                ipv4=proxmox.vm.VirtualMachineInitializationIpConfigIpv4Args(
                                    address=new_address,
                                    gateway=gateway
                                )
                            )
                        )

                for ssk_keys_entry in v['cloud_init']['user_account']['keys']:
                    ssh_keys.append(ssk_keys_entry)

                if os.getenv("SSH_PUB_KEY"):
                    ssh_keys.append(os.getenv("SSH_PUB_KEY"))

                for net_entry in v['network_devices']:
                    for n in net_entry:
                        print(f"NETWORK INTERFACES:: {n}")
                        nets.append(
                            proxmox.vm.VirtualMachineNetworkDeviceArgs(
                                bridge=net_entry[n]['bridge'],
                                model=net_entry[n]['model'],
                                vlan_id=net_entry[n]['vlan_id']
                            )
                        )

                virtual_machine = proxmox.vm.VirtualMachine(
                    vm_id=base_vm_id[0] + vmcount,
                    resource_name=f"{base_resource_name}-{name_counter:03d}",
                    node_name=node_name,
                    agent=proxmox.vm.VirtualMachineAgentArgs(
                        enabled=v['agent']['enabled'],
                        # trim=v['agent']['trim'],
                        type=v['agent']['type']
                    ),
                    bios=v['bios'],
                    cpu=proxmox.vm.VirtualMachineCpuArgs(
                        cores=v['cpu']['cores'],
                        sockets=v['cpu']['sockets'],
                        type="kvm64"
                    ),
                    clone=proxmox.vm.VirtualMachineCloneArgs(
                        node_name=node_name,
                        vm_id=v["clone_vm_id"],
                        full=v['clone']['full'],
                    ),
                    disks=disks,
                    memory=proxmox.vm.VirtualMachineMemoryArgs(
                        dedicated=v['memory']['dedicated']
                    ),
                    name=f"{base_resource_name}-{name_counter:03d}",
                    network_devices=nets,
                    initialization=proxmox.vm.VirtualMachineInitializationArgs(
                        type=v['cloud_init']['type'],
                        datastore_id=v['cloud_init']['datastore_id'],
                        interface=v['cloud_init']['interface'],
                        dns=proxmox.vm.VirtualMachineInitializationDnsArgs(
                            domain=v['cloud_init']['dns']['domain'],
                            servers=v['cloud_init']['dns']['servers']
                        ),
                        ip_configs=ip_configs,
                        user_account=proxmox.vm.VirtualMachineInitializationUserAccountArgs(
                            username=os.getenv("VM_USER"),
                            password=os.getenv("VM_PASS"),
                            keys=ssh_keys
                        ),
                    ),
                    on_boot=v['on_boot'],
                    reboot=v['on_boot'],
                    opts=pulumi.ResourceOptions(provider=provider,ignore_changes=v['ignore_changes'],depends_on=dependencies),
                )

                vm_details = Output.all(virtual_machine.name, virtual_machine.id) \
                .apply(lambda args: {
                    args[0]: args[1]
                })
                # vm_id = virtual_machine.id.apply(lambda id: virtual_machine.id)
                # vm_name = f"{base_resource_name}-{name_counter}",
                vm_ids.append(vm_details)

                # wait30_seconds = time.Sleep(f"wait30Seconds-{base_resource_name}-{name_counter:03d}-build", create_duration="30s", opts=pulumi.ResourceOptions(depends_on=[virtual_machine]))

                # dependencies.append(wait30_seconds)
                dependencies.append(virtual_machine)

                pulumi.export(v['name'], virtual_machine.id)
            #
            # Run bootstrap process
            # WAIT FOR VM's to be built.

        elif v["vm_type"] == "gpu-agent":
            for vmcount in range(v['count']):
                base_resource_name=v['environment'] + "-" + v['resource_name'] + "-" + v['vm_type']
                name_counter = vmcount + 1
                base_vm_id=v['vm_id'],

                if providers[vmcount]["hostpcis"] == "gpu":
                    provider = providers[vmcount]["provider"]
                    node_name = providers[vmcount]["node_name"]
                    hostpcis = providers[vmcount]["hostpcis"]
                else:
                    continue

                for disk_entry in v['disks']:
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

                for ip_config_entry in v['cloud_init']['ip_configs']:
                    ipv4 = ip_config_entry.get('ipv4')

                    if ipv4:
                        new_address = ''
                        ip, subnet = ipv4.get('address', '').split('/')
                        gateway = ipv4.get('gateway')
                        new_ip = str(ipaddress.ip_address(ip) + vmcount)
                        new_address = f"{new_ip}/{subnet}"

                        ip_configs = []
                        ip_configs.append(
                            proxmox.vm.VirtualMachineInitializationIpConfigArgs(
                                ipv4=proxmox.vm.VirtualMachineInitializationIpConfigIpv4Args(
                                    address=new_address,
                                    gateway=gateway
                                )
                            )
                        )

                for ssk_keys_entry in v['cloud_init']['user_account']['keys']:
                    ssh_keys.append(ssk_keys_entry)

                if os.getenv("SSH_PUB_KEY"):
                    ssh_keys.append(os.getenv("SSH_PUB_KEY"))

                for net_entry in v['network_devices']:
                    for n in net_entry:
                        print(f"NETWORK INTERFACES:: {n}")
                        nets.append(
                            proxmox.vm.VirtualMachineNetworkDeviceArgs(
                                bridge=net_entry[n]['bridge'],
                                model=net_entry[n]['model'],
                                vlan_id=net_entry[n]['vlan_id']
                            )
                        )

                hostpcis=proxmoxve.vm.VirtualMachineHostpciArgs(
                            device="hostpci0",
                            mapping=hostpcis,
                        )
                
                virtual_machine = proxmox.vm.VirtualMachine(
                    vm_id=base_vm_id[0] + vmcount,
                    resource_name=f"{base_resource_name}-{name_counter:03d}",
                    node_name=node_name,
                    agent=proxmox.vm.VirtualMachineAgentArgs(
                        enabled=v['agent']['enabled'],
                        # trim=v['agent']['trim'],
                        type=v['agent']['type']
                    ),
                    bios=v['bios'],
                    cpu=proxmox.vm.VirtualMachineCpuArgs(
                        cores=v['cpu']['cores'],
                        sockets=v['cpu']['sockets'],
                        type="kvm64"
                    ),
                    clone=proxmox.vm.VirtualMachineCloneArgs(
                        node_name=node_name,
                        vm_id=v["clone_vm_id"],
                        full=v['clone']['full'],
                    ),
                    disks=disks,
                    memory=proxmox.vm.VirtualMachineMemoryArgs(
                        dedicated=v['memory']['dedicated']
                    ),
                    name=f"{base_resource_name}-{name_counter:03d}",
                    network_devices=nets,
                    hostpcis=[hostpcis],
                    initialization=proxmox.vm.VirtualMachineInitializationArgs(
                        type=v['cloud_init']['type'],
                        datastore_id=v['cloud_init']['datastore_id'],
                        interface=v['cloud_init']['interface'],
                        dns=proxmox.vm.VirtualMachineInitializationDnsArgs(
                            domain=v['cloud_init']['dns']['domain'],
                            servers=v['cloud_init']['dns']['servers']
                        ),
                        ip_configs=ip_configs,
                        user_account=proxmox.vm.VirtualMachineInitializationUserAccountArgs(
                            username=os.getenv("VM_USER"),
                            password=os.getenv("VM_PASS"),
                            keys=ssh_keys
                        ),
                    ),
                    on_boot=v['on_boot'],
                    reboot=v['on_boot'],
                    opts=pulumi.ResourceOptions(provider=provider,ignore_changes=v['ignore_changes'],depends_on=dependencies),
                )

                vm_details = Output.all(virtual_machine.name, virtual_machine.id) \
                .apply(lambda args: {
                    args[0]: args[1]
                })
                # vm_id = virtual_machine.id.apply(lambda id: virtual_machine.id)
                # vm_name = f"{base_resource_name}-{name_counter}",
                vm_ids.append(vm_details)

                # wait30_seconds = time.Sleep(f"wait30Seconds-{base_resource_name}-{name_counter:03d}-build", create_duration="30s", opts=pulumi.ResourceOptions(depends_on=[virtual_machine]))

                # dependencies.append(wait30_seconds)
                dependencies.append(virtual_machine)

                pulumi.export(v['name'], virtual_machine.id)
            #
            # Run bootstrap process
            # WAIT FOR VM's to be built.


for vm in parsed_data:
    environments = ["dev", "prod"]
    result_data = []
    for v in vm:
        for env in environments:
            if env == v["environment"]:
                # Loop through count of VM's and customize dict for bootstrap.
                for vmcount in range(v['count']):
                    for ip_config_entry in v['cloud_init']['ip_configs']:
                        ipv4 = ip_config_entry.get('ipv4')

                        if ipv4:
                            new_address = ''
                            ip, subnet = ipv4.get('address', '').split('/')
                            gateway = ipv4.get('gateway')
                            new_ip = str(ipaddress.ip_address(ip) + vmcount)
                    
                    name_counter = vmcount + 1

                    server_ip = get_server_ip(parsed_data, v["environment"])
                    data = {
                        "name": v['environment'] + "-" + v["resource_name"] + "-" + f"{name_counter:03d}",
                        "environment": v["environment"],
                        "vm_type": v["vm_type"],
                        "ip": new_ip,
                        "server_ip": server_ip,
                        "user": v['cloud_init']['user_account']['username'],
                        "ssh_pub_key": os.getenv("SSH_PUB_KEY"),
                        "ssh_priv_key": os.getenv("SSH_PRIV_KEY"),
                        "tls_san": v["tls_san"]
                    }

                    result_data.append(data)
                    name = data["name"]
                    print(f"Adding {name} to result_data")
                    # wait10_seconds = time.Sleep(f"wait10Seconds-{name}-pre-bootstrap", create_duration="10s", opts=pulumi.ResourceOptions())
        # print(result_data)
        # wait30_seconds = time.Sleep(f"wait30Seconds-{v['environment']}-{v['resource_name']}-{vmcount:03d}-pre-bootstrap", create_duration="30s", opts=pulumi.ResourceOptions())
        control_vms_bootstrap = bootstrap.bootstrap(result_data, dependencies)

    pulumi.export(f"VM ID's", vm_ids)
