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

def bootstrap(node_list, dependencies):
    for index, item in enumerate(node_list):
    #     print(index, item)
    # for i in node_list:
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
            per_dial_timeout = per_dial_timeout,
        )
        copy_file_resource = remote.CopyFile(f"copyFileResource-{name}-{ip}",
            connection=connection,
            local_path="files/k3sup_install.sh",
            remote_path="/tmp/k3sup_install.sh",
            triggers=["any"],
            opts=pulumi.ResourceOptions(depends_on=dependencies)
        )
        if item["vm_type"] == "server" and index == 0:
            command_k3sup_install_resource = remote.Command(f"commandResource-install-{name}",
                connection=connection,
                create=f'sh /tmp/k3sup_install.sh install {item["server_ip"]} {item["ip"]} {item["user"]} "{item["ssh_priv_key"]}" {item["tls_san"]}',
                update=f'sh /tmp/k3sup_install.sh install {item["server_ip"]} {item["ip"]} {item["user"]} "{item["ssh_priv_key"]}" {item["tls_san"]}',
                opts=pulumi.ResourceOptions(depends_on=[copy_file_resource])
            )
            wait30_seconds = time.Sleep(f"wait30Seconds-{item['name']}-install-bootstrap", create_duration="30s", opts=pulumi.ResourceOptions(depends_on=[command_k3sup_install_resource]))
            copy_cilium_resource = remote.CopyFile(f"copyCiliumInstallFileResource-{name}-{ip}",
                connection=connection,
                local_path="files/cilium_install.sh",
                remote_path="/tmp/cilium_install.sh",
                triggers=["any"],
                opts=pulumi.ResourceOptions(depends_on=[command_k3sup_install_resource, wait30_seconds])
            )
            command_cilium_install_resource = remote.Command(f"commandCiliumResource-install-{name}",
                connection=connection,
                create=f'sh /tmp/cilium_install.sh',
                update=f'sh /tmp/cilium_install.sh',
                opts=pulumi.ResourceOptions(depends_on=[copy_cilium_resource])
            )

        elif item["vm_type"] == "server" and index >= 1:
            wait30_seconds = time.Sleep(f"wait30Seconds-{item['name']}-server-bootstrap", create_duration="30s", opts=pulumi.ResourceOptions(depends_on=[copy_cilium_resource]))
            command_k3sup_server_resource = remote.Command(f"commandResource-server-{name}",
                connection=connection,
                create=f'sh /tmp/k3sup_install.sh server {item["server_ip"]} {item["ip"]} {item["user"]} "{item["ssh_priv_key"]}" {item["tls_san"]}',
                update=f'sh /tmp/k3sup_install.sh server {item["server_ip"]} {item["ip"]} {item["user"]} "{item["ssh_priv_key"]}" {item["tls_san"]}',
                opts=pulumi.ResourceOptions(depends_on=[copy_file_resource, command_cilium_install_resource, wait30_seconds])
            )
        elif item["vm_type"] == "agent":
            wait30_seconds = time.Sleep(f"wait30Seconds-{item['name']}-agent-bootstrap", create_duration="30s", opts=pulumi.ResourceOptions(depends_on=[copy_file_resource]))
            command_k3sup_agent_resource = remote.Command(f"commandResource-agent-{name}",
                connection=connection,
                create=f'sh /tmp/k3sup_install.sh agent {item["server_ip"]} {item["ip"]} {item["user"]} "{item["ssh_priv_key"]}" {item["tls_san"]}',
                update=f'sh /tmp/k3sup_install.sh agent {item["server_ip"]} {item["ip"]} {item["user"]} "{item["ssh_priv_key"]}" {item["tls_san"]}',
                opts=pulumi.ResourceOptions(depends_on=[copy_file_resource, wait30_seconds])
            )
