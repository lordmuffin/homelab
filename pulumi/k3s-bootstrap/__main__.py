"""A Python Pulumi program"""
import os,yaml
import pulumi
from pulumi import Output
import pulumi_proxmoxve as proxmoxve
from pulumi_command import local, remote
# import files.vm as vm
import files.vm_bootstrap as bootstrap

folder_path = "../config/vms/"

def load_yaml_files_from_folder(folder_path):
    yaml_files = [file for file in os.listdir(folder_path) if file.endswith(".yaml")]
    loaded_data = []

    for yaml_file in yaml_files:
        file_path = os.path.join(folder_path, yaml_file)
        with open(file_path, 'r') as file:
            yaml_data = yaml.safe_load(file)
            loaded_data.append(yaml_data)

    return loaded_data

parsed_data = load_yaml_files_from_folder(folder_path)

for vm in parsed_data:
    result_data = []

    for v in vm:
        for vmcount in range(v['count']):
            name_counter = vmcount + 1
            for ip_config_entry in v['cloud_init']['ip_configs']:
                ipv4 = ip_config_entry.get('ipv4')

                if ipv4:
                    new_address = ''
                    ip, subnet = ipv4.get('address', '').split('/')

            data = {
                "name": v["resource_name"] + "-" + f"{name_counter:03d}",
                "ip": ip,
                "ssh_pub_key": os.getenv("SSH_PUB_KEY"),
                "ssh_priv_key": os.getenv("SSH_PRIV_KEY")
            }
            result_data.append(data)
print(result_data)
control_vms_bootstrap = bootstrap.bootstrap(result_data)
