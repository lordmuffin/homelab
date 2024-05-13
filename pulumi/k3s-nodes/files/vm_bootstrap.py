import os
import pulumi
from pulumi import Output
import pulumi_proxmoxve as proxmoxve
from pulumi_command import local, remote
import time

# Get List of IP's
# Remote into IP's and copy bootstrap script?
# Execute bootstrap script?
# Copy k3sup install? Or possibly run locally? 

def bootstrap(node_list, dependencies):
    for i in node_list:
        name = i["name"]
        ip = i["ip"]
        print(i["ip"])
        connection = remote.ConnectionArgs(
            host=ip,
            user="ubuntu",
            # password="ubuntu"
            private_key=os.getenv("SSH_PRIV_KEY"),
            private_key_password=None,
        )
        copy_file_resource = remote.CopyFile(f"copyFileResource-{name}-{ip}",
            connection=connection,
            local_path="files/k3sup_install.sh",
            remote_path="/tmp/k3sup_install.sh",
            triggers=["any"],
            opts=pulumi.ResourceOptions(depends_on=dependencies)
        )
        # time.sleep(10)
        command_k3sup_install_resource = remote.Command(f"commandResource-install-{name}",
            connection=connection,
            create=f'sh /tmp/k3sup_install.sh install {i["server_ip"]} {i["ip"]} {i["user"]} "{i["ssh_priv_key"]}"',
            # update=f'K3SUP_NODE_TYPE=install SERVER_IP={i["server_ip"]} NEXT_SERVER_IP={i["ip"]} USER={i["user"]} bash /tmp/k3sup_install.sh',
            # environment={
            #     "K3SUP_NODE_TYPE": "install",
            #     "SERVER_IP": i["server_ip"],
            #     "NEXT_SERVER_IP": i["ip"],
            #     "USER": i["user"]
            # },
            opts=pulumi.ResourceOptions(depends_on=[copy_file_resource])


        )