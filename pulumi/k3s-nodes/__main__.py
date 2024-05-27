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
import files.vm_bootstrap as bootstrap

providers_path = "../config/providers/"
folder_path = "../config/vms/"

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
    loaded_data = []

    for yaml_file in yaml_files:
        file_path = os.path.join(folder_path, yaml_file)
        with open(file_path, 'r') as file:
            yaml_data = yaml.safe_load(file)
            loaded_data.append(yaml_data)

    return loaded_data

def vm_virtual_machine(i, name, node_name, opts):
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

    for ip_config_entry in i['cloud_init']['ip_configs']:
        ipv4 = ip_config_entry.get('ipv4')
        ip = ipv4.get('address')
        gateway = ipv4.get('gateway')

        ip_configs = []
        ip_configs.append(
            proxmox.vm.VirtualMachineInitializationIpConfigArgs(
                ipv4=proxmox.vm.VirtualMachineInitializationIpConfigIpv4Args(
                    address=ip,
                    gateway=gateway
                )
            )
        )

    for ssk_keys_entry in i['cloud_init']['user_account']['keys']:
        ssh_keys.append(ssk_keys_entry)

    if os.getenv("SSH_PUB_KEY"):
        ssh_keys.append(os.getenv("SSH_PUB_KEY"))

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
    
    agent = proxmox.vm.VirtualMachineAgentArgs(
                        enabled=i['agent']['enabled'],
                        # trim=v['agent']['trim'],
                        type=i['agent']['type']
                    )
    cpu=proxmox.vm.VirtualMachineCpuArgs(
                        cores=i['cpu']['cores'],
                        sockets=i['cpu']['sockets'],
                        type="kvm64"
                    )
    clone=proxmox.vm.VirtualMachineCloneArgs(
                        node_name=node_name,
                        vm_id=i["clone_vm_id"],
                        full=i['clone']['full'],
                    )
    memory=proxmox.vm.VirtualMachineMemoryArgs(
                        dedicated=i['memory']['dedicated']
                    )
    initialization=proxmox.vm.VirtualMachineInitializationArgs(
                        type=i['cloud_init']['type'],
                        datastore_id=i['cloud_init']['datastore_id'],
                        interface=i['cloud_init']['interface'],
                        dns=proxmox.vm.VirtualMachineInitializationDnsArgs(
                            domain=i['cloud_init']['dns']['domain'],
                            servers=i['cloud_init']['dns']['servers']
                        ),
                        ip_configs=ip_configs,
                        user_account=proxmox.vm.VirtualMachineInitializationUserAccountArgs(
                            username=i['cloud_init']['user_account']['username'],
                            password=i['cloud_init']['user_account']['password'],
                            keys=ssh_keys
                        ),
                    )
    vm = proxmox.vm.VirtualMachine(
        vm_id=base_vm_id[0],
        resource_name=name,
        node_name=node_name,
        agent=agent,
        bios=i['bios'],
        cpu=cpu,
        clone=clone,
        disks=disks,
        memory=memory,
        name=name,
        network_devices=nets,
        initialization=initialization,
        on_boot=i['on_boot'],
        reboot=i['on_boot'],
        opts=opts
    )
    return vm

# Gather Data
# environments = load_folders_from_path(folder_path)
parsed_data = load_yaml_files_from_folder(folder_path)
providers_data = load_yaml_files_from_folder(providers_path)

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
        tmp_p["provider"] = provider

        providers.append(tmp_p)

# Build VM's
for file in parsed_data:
    disks = []
    nets = []
    ip_configs = []
    ssh_keys = []
    vm_ids = []
    public_ip_addresses = [] # create an array to store the information
    dependencies = []

    for v in file:
        base_resource_name=v['environment'] + "-" + v['resource_name'] + "-" + v['vm_type']
        random4 = random_char(4)
        name = v["environment"] + "-" + v["resource_name"] + "-" + v["vm_type"] + "-" + v["suffix"]

        if v["vm_type"] == "server":
            for p in providers:
                if p["node_name"] == v["node_name"]:
                    current_provider = p["provider"]

                    virtual_machine = vm_virtual_machine(
                        i=v,
                        name=name,
                        node_name=v["node_name"],
                        opts=pulumi.ResourceOptions(provider=current_provider,ignore_changes=v['ignore_changes']),
                    )

                    vm_details = Output.all(virtual_machine.name, virtual_machine.id) \
                    .apply(lambda args: {
                        args[0]: args[1]
                    })

                    vm_ids.append(vm_details)

                    dependencies.append(virtual_machine)

                    pulumi.export(v['name'], virtual_machine.id)

        elif v["vm_type"] == "agent":
            for p in providers:
                if p["node_name"] == v["node_name"]:
                    current_provider = p["provider"]

                    virtual_machine = vm_virtual_machine(
                        i=v,
                        name=name,
                        node_name=v["node_name"],
                        opts=pulumi.ResourceOptions(provider=current_provider,ignore_changes=v['ignore_changes']),
                    )

                    vm_details = Output.all(virtual_machine.name, virtual_machine.id) \
                    .apply(lambda args: {
                        args[0]: args[1]
                    })

                    vm_ids.append(vm_details)

                    dependencies.append(virtual_machine)

                    pulumi.export(v['name'], virtual_machine.id)

        elif v["vm_type"] == "gpu-agent":
            for p in providers:
                if p["node_name"] == v["node_name"]:
                    current_provider = p["provider"]

                    virtual_machine = vm_virtual_machine(
                        i=v,
                        name=name,
                        node_name=v["node_name"],
                        opts=pulumi.ResourceOptions(provider=current_provider,ignore_changes=v['ignore_changes']),
                    )

                    vm_details = Output.all(virtual_machine.name, virtual_machine.id) \
                    .apply(lambda args: {
                        args[0]: args[1]
                    })

                    vm_ids.append(vm_details)

                    dependencies.append(virtual_machine)

                    pulumi.export(v['name'], virtual_machine.id)



# Bootstrap
for file in parsed_data:
    environments = ["dev", "prod"]
    primary_server_ip = [{
        "environment": "dev",
        "ip": "192.168.10.30",
    },
    {
        "environment": "prod",
        "ip": "192.168.11.30",
    }]
    result_data = []

    for v in file:
        for env in environments:
            if env == v["environment"]:
                for ip_config_entry in v['cloud_init']['ip_configs']:
                    ipv4 = ip_config_entry.get('ipv4')
                    ip, subnet = ipv4.get('address', '').split('/')
                    gateway = ipv4.get('gateway')
                
                for env in primary_server_ip:
                    if env["environment"] == v["environment"]:
                        server_ip = env["ip"]

                data = {
                    "name": v["environment"] + "-" + v["resource_name"] + "-" + v["vm_type"] + "-" + v["suffix"],
                    "environment": v["environment"],
                    "vm_type": v["vm_type"],
                    "ip": ip,
                    "server_ip": server_ip,
                    "user": v['cloud_init']['user_account']['username'],
                    "ssh_pub_key": os.getenv("SSH_PUB_KEY"),
                    "ssh_priv_key": os.getenv("SSH_PRIV_KEY"),
                    "tls_san": v["tls_san"]
                }

                result_data.append(data)
                name = data["name"]
                print(f"Adding {name} to result_data")

        # print(result_data)
        control_vms_bootstrap = bootstrap.bootstrap(result_data, dependencies)

    pulumi.export(f"VM ID's", vm_ids)
