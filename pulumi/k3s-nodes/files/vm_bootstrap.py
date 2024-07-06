import os
import pulumi
from pulumi import Output
import pulumi_proxmoxve as proxmoxve
from pulumi_command import local, remote
import pulumiverse_time as time
# import time

# Get List of IP's
# Remote into IP's and copy bootstrap script?
# Execute bootstrap script?
# Copy k3sup install? Or possibly run locally? 
dial_error_limit = 10
per_dial_timeout = 120
count = 0

def bootstrap(node_list, dependencies):
    bootstrap_count = count + 1
    env = node_list[0]["environment"]
    init_dep = []
    server_dep = []
    # wait60_seconds = time.Sleep(f"wait60Seconds-pre-install-bootstrap", create_duration="30s", opts=pulumi.ResourceOptions(depends_on=dependencies))
    
    print(node_list)

    for item in node_list:

        name = item["name"]
        ip = item["ip"]
        print(item["ip"])
        connection = remote.ConnectionArgs(
            host=ip,
            user="ubuntu",
            # password="ubuntu"
            private_key=os.getenv("SSH_PRIV_KEY"),
            private_key_password=None,
            dial_error_limit = dial_error_limit,
            per_dial_timeout = per_dial_timeout
        )
        copy_file_resource = remote.CopyFile(f"copyFileResource-{name}-{ip}",
            connection=connection,
            local_path="files/k3sup_install.sh",
            remote_path="/tmp/k3sup_install.sh",
            triggers=["any"],
            opts=pulumi.ResourceOptions()
        )
        if item["vm_type"] == "server" and item["suffix"] == "001":
            command_k3sup_install_resource = remote.Command(f"commandResource-install-{name}",
                connection=connection,
                create=f'sh /tmp/k3sup_install.sh install {item["server_ip"]} {item["ip"]} {item["user"]} "{item["ssh_priv_key"]}" {item["tls_san"]}',
                update=f'sh /tmp/k3sup_install.sh install {item["server_ip"]} {item["ip"]} {item["user"]} "{item["ssh_priv_key"]}" {item["tls_san"]}',
                opts=pulumi.ResourceOptions(depends_on=[copy_file_resource])
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
                create=f'sh /tmp/cilium_install.sh {item["server_ip"]}',
                update=f'sh /tmp/cilium_install.sh {item["server_ip"]}',
                opts=pulumi.ResourceOptions(depends_on=[copy_cilium_resource])
            )
            init_dep.append(command_cilium_install_resource)
            wait15_seconds_server = time.Sleep(f"wait15Seconds-server-{item['name']}-server-bootstrap", create_duration="15s", opts=pulumi.ResourceOptions(depends_on=[command_cilium_install_resource]))

    for item in node_list:
        if item["vm_type"] == "server" and item["suffix"] != "001":
            command_k3sup_server_resource = remote.Command(f"commandResource-server-{name}",
                connection=connection,
                create=f'sh /tmp/k3sup_install.sh server {item["server_ip"]} {item["ip"]} {item["user"]} "{item["ssh_priv_key"]}" {item["tls_san"]}',
                update=f'sh /tmp/k3sup_install.sh server {item["server_ip"]} {item["ip"]} {item["user"]} "{item["ssh_priv_key"]}" {item["tls_san"]}',
                opts=pulumi.ResourceOptions(depends_on=init_dep)
            )

    for item in node_list:
        # elif item["vm_type"] == "agent" or item["vm_type"] == "gpu-agent":
        if item["vm_type"] == "agent" or item["vm_type"] == "gpu-agent" :
            command_k3sup_agent_resource = remote.Command(f"commandResource-agent-{name}",
                connection=connection,
                create=f'sh /tmp/k3sup_install.sh agent {item["server_ip"]} {item["ip"]} {item["user"]} "{item["ssh_priv_key"]}" {item["tls_san"]}',
                update=f'sh /tmp/k3sup_install.sh agent {item["server_ip"]} {item["ip"]} {item["user"]} "{item["ssh_priv_key"]}" {item["tls_san"]}',
                opts=pulumi.ResourceOptions(depends_on=init_dep)
            )
