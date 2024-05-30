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
folder_path = "../config/vms/"
dev_cluster_path = "../config/dev-lab/"

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

def vm_virtual_machine(i, name, node_name, provider, depends_on, ignore_changes):
    base_vm_id=i['vm_id'],
    username = i['cloud_init']['user_account']['username']

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
                            username=username,
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
        opts=pulumi.ResourceOptions(provider=provider,ignore_changes=ignore_changes, depends_on=depends_on)
    )

    name = name
    dial_error_limit = 10
    per_dial_timeout = 30
    private_key = os.getenv("SSH_PRIV_KEY")

    environments = ["dev", "prod"]
    primary_server_ip = [{
        "environment": "dev",
        "ip": "192.168.10.30",
    },
    {
        "environment": "prod",
        "ip": "192.168.11.30",
    }]

    for ip_config_entry in v['cloud_init']['ip_configs']:
        ipv4 = ip_config_entry.get('ipv4')
        ip, subnet = ipv4.get('address', '').split('/')
        gateway = ipv4.get('gateway')

    for env in environments:
        if env == i["environment"]:
            for env in primary_server_ip:
                if env["environment"] == i["environment"]:
                    server_ip = env["ip"]

    connection = remote.ConnectionArgs(
        host=ip,
        user=username,
        # password="ubuntu"
        private_key=private_key,
        private_key_password=None,
        dial_error_limit = dial_error_limit,
        per_dial_timeout = per_dial_timeout
    )
    wait_for_vm = time.Sleep(f"wait30Seconds-wait-for-vm-{name}", create_duration="30s", opts=pulumi.ResourceOptions(depends_on=vm))
    copy_file_resource = remote.CopyFile(f"copyFileResource-{name}-{ip}",
        connection=connection,
        local_path="files/k3sup_install.sh",
        remote_path="/tmp/k3sup_install.sh",
        triggers=["any"],
        opts=pulumi.ResourceOptions(depends_on=[wait_for_vm])
    )
    wait_for_copy = time.Sleep(f"wait30Seconds-wait-for-copy-{name}", create_duration="30s", opts=pulumi.ResourceOptions(depends_on=copy_file_resource))

    if i["vm_type"] == "server" and i["suffix"] == "001":
        command_k3sup_install_resource = remote.Command(f"commandResource-install-{name}",
            connection=connection,
            create=f'sh /tmp/k3sup_install.sh install {server_ip} {ip} {username} "{private_key}" {i["tls_san"]}',
            update=f'sh /tmp/k3sup_install.sh install {server_ip} {ip} {username} "{private_key}" {i["tls_san"]}',
            opts=pulumi.ResourceOptions(depends_on=[wait_for_copy])
        )
        copy_cilium_resource = remote.CopyFile(f"copyCiliumInstallFileResource-{name}-{ip}",
            connection=connection,
            local_path="files/cilium_install.sh",
            remote_path="/tmp/cilium_install.sh",
            triggers=["any"],
            opts=pulumi.ResourceOptions(depends_on=[command_k3sup_install_resource])
        )
        command_cilium_install_resource = remote.Command(f"commandCiliumResource-install-{name}",
            connection=connection,
            create=f'sh /tmp/cilium_install.sh {server_ip}',
            update=f'sh /tmp/cilium_install.sh {server_ip}',
            opts=pulumi.ResourceOptions(depends_on=[copy_cilium_resource])
        )
        wait_for_cilium = time.Sleep(f"wait30Seconds-wait-for-cilium-{name}", create_duration="30s", opts=pulumi.ResourceOptions(depends_on=command_cilium_install_resource))

    if i["vm_type"] == "server" and i["suffix"] != "001":
        command_k3sup_server_resource = remote.Command(f"commandResource-server-{name}",
            connection=connection,
            create=f'sh /tmp/k3sup_install.sh server {server_ip} {ip} {username} "{private_key}" {i["tls_san"]}',
            update=f'sh /tmp/k3sup_install.sh server {server_ip} {ip} {username} "{private_key}" {i["tls_san"]}',
            opts=pulumi.ResourceOptions(depends_on=[wait_for_copy])
        )

    if i["vm_type"] == "agent" or i["vm_type"] == "gpu-agent" :
        command_k3sup_agent_resource = remote.Command(f"commandResource-agent-{name}",
            connection=connection,
            create=f'sh /tmp/k3sup_install.sh agent {server_ip} {ip} {username} "{private_key}" {i["tls_san"]}',
            update=f'sh /tmp/k3sup_install.sh agent {server_ip} {ip} {username} "{private_key}" {i["tls_san"]}',
            opts=pulumi.ResourceOptions(depends_on=[wait_for_copy])
        )

    wait_for_vm = time.Sleep(f"wait90Seconds-post-create-{name}", create_duration="90s", opts=pulumi.ResourceOptions(depends_on=wait_for_copy))

    return vm



# Gather Data
# environments = load_folders_from_path(folder_path)
# parsed_data = load_yaml_files_from_foldedr(folder_path)
providers_data = load_yaml_files_from_folder(providers_path)
dev_cluster_data_servers = load_yaml_files_from_folder(dev_cluster_path + "servers/")
dev_cluster_data_agents = load_yaml_files_from_folder(dev_cluster_path + "agents/")

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

agent_depends_on = []
pause = time.Sleep(f"wait30Seconds-pre-server-create", create_duration="30s", opts=pulumi.ResourceOptions())
agent_depends_on.append(pause)


# dev-lab cluster Server builds
for file in dev_cluster_data_servers:
    disks = []
    nets = []
    ip_configs = []
    ssh_keys = []
    vm_ids = []
    public_ip_addresses = [] # create an array to store the information
    dependencies = []
    server_vms = []
    depends_on = []

    for v in file:
        base_resource_name=v['environment'] + "-" + v['resource_name'] + "-" + v['vm_type']
        name = v["environment"] + "-" + v["resource_name"] + "-" + v["vm_type"] + "-" + v["suffix"]

        for p in providers:
            if p["node_name"] == v["node_name"]:
                current_provider = p["provider"]

                virtual_machine = vm_virtual_machine(
                    i=v,
                    name=name,
                    node_name=v["node_name"],
                    provider=current_provider,
                    depends_on=agent_depends_on,
                    ignore_changes=v['ignore_changes'],
                )
                agent_depends_on.append(virtual_machine) #ERROR - This is not getting item before next loop starts.

pause = time.Sleep(f"wait30Seconds-pre-vm-create", create_duration="30s", opts=pulumi.ResourceOptions())
agent_depends_on.append(pause)

# dev-lab cluster Agent builds
for file in dev_cluster_data_agents:
    disks = []
    nets = []
    ip_configs = []
    ssh_keys = []
    vm_ids = []
    public_ip_addresses = [] # create an array to store the information
    dependencies = []
    server_init_complete = False

    for v in file:
        base_resource_name=v['environment'] + "-" + v['resource_name'] + "-" + v['vm_type']
        name = v["environment"] + "-" + v["resource_name"] + "-" + v["vm_type"] + "-" + v["suffix"]

        for p in providers:
            if p["node_name"] == v["node_name"]:
                current_provider = p["provider"]

                virtual_machine = vm_virtual_machine(
                    i=v,
                    name=name,
                    node_name=v["node_name"],
                    provider=current_provider, 
                    depends_on=agent_depends_on,
                    ignore_changes=v['ignore_changes']),




# # Build VM's
# for file in parsed_data:
#     disks = []
#     nets = []
#     ip_configs = []
#     ssh_keys = []
#     vm_ids = []
#     public_ip_addresses = [] # create an array to store the information
#     dependencies = []
#     server_init_complete = False

#     for v in file:
#         base_resource_name=v['environment'] + "-" + v['resource_name'] + "-" + v['vm_type']
#         random4 = random_char(4)
#         name = v["environment"] + "-" + v["resource_name"] + "-" + v["vm_type"] + "-" + v["suffix"]

#         if v["vm_type"] == "server":
#             for p in providers:
#                 if p["node_name"] == v["node_name"]:
#                     current_provider = p["provider"]

#                     virtual_machine = vm_virtual_machine(
#                         i=v,
#                         name=name,
#                         node_name=v["node_name"],
#                         opts=pulumi.ResourceOptions(provider=current_provider,ignore_changes=v['ignore_changes']),
#                     )
#                     server_init_complete = True


#         elif v["vm_type"] == "agent":
#             for p in providers:
#                 if p["node_name"] == v["node_name"]:
#                     current_provider = p["provider"]

#                     virtual_machine = vm_virtual_machine(
#                         i=v,
#                         name=name,
#                         node_name=v["node_name"],
#                         opts=pulumi.ResourceOptions(provider=current_provider,ignore_changes=v['ignore_changes']),
#                     )

#         elif v["vm_type"] == "gpu-agent":
#             for p in providers:
#                 if p["node_name"] == v["node_name"]:
#                     current_provider = p["provider"]

#                     virtual_machine = vm_virtual_machine(
#                         i=v,
#                         name=name,
#                         node_name=v["node_name"],
#                         opts=pulumi.ResourceOptions(provider=current_provider,ignore_changes=v['ignore_changes']),
#                     )

#         vm_details = Output.all(virtual_machine.name, virtual_machine.ipv4_addresses) \
#         .apply(lambda args: {
#             args[0]: args[1]
#         })

#         vm_ids.append(vm_details)

#         dependencies.append(virtual_machine)

#         pulumi.export("VM IP's", vm_details)
#         pulumi.export(v['name'], virtual_machine.id)


# Bootstrap
# for file in parsed_data:
#     environments = ["dev", "prod"]
#     primary_server_ip = [{
#         "environment": "dev",
#         "ip": "192.168.10.30",
#     },
#     {
#         "environment": "prod",
#         "ip": "192.168.11.30",
#     }]
#     result_data = []

#     for v in file:
#         for env in environments:
#             if env == v["environment"]:
#                 for ip_config_entry in v['cloud_init']['ip_configs']:
#                     ipv4 = ip_config_entry.get('ipv4')
#                     ip, subnet = ipv4.get('address', '').split('/')
#                     gateway = ipv4.get('gateway')
                
#                 for env in primary_server_ip:
#                     if env["environment"] == v["environment"]:
#                         server_ip = env["ip"]

#                 data = {
#                     "name": v["environment"] + "-" + v["resource_name"] + "-" + v["vm_type"] + "-" + v["suffix"],
#                     "environment": v["environment"],
#                     "vm_type": v["vm_type"],
#                     "ip": ip,
#                     "server_ip": server_ip,
#                     "suffix": v["suffix"],
#                     "user": v['cloud_init']['user_account']['username'],
#                     "ssh_pub_key": os.getenv("SSH_PUB_KEY"),
#                     "ssh_priv_key": os.getenv("SSH_PRIV_KEY"),
#                     "tls_san": v["tls_san"]
#                 }

#                 result_data.append(data)
#                 name = data["name"]
#                 print(f"Adding {name} to result_data")

#         # print(result_data)
#         control_vms_bootstrap = bootstrap.bootstrap(result_data, dependencies)

#     pulumi.export(f"VM ID's", vm_ids)
