import os
import pulumi
from pulumi import Output
import pulumi_proxmoxve as proxmoxve
from pulumi_command import local, remote
import time

# Get List of IP's
# Remote into IP's and copy cilium script?
# Execute cilium script?
# Copy k3sup install? Or possibly run locally? 

def cilium(node_list):
    for i in node_list:
        name = i["name"]
        ip = i["ip"]
        print(i["ip"])
        connection = remote.ConnectionArgs(
            host=ip,
            user="kairos",
            # password="ubuntu"
            private_key=i["ssh_priv_key"],
            private_key_password=None,
        )
        copy_file_resource = remote.CopyFile(f"copyFileResource-{name}-{ip}",
            connection=connection,
            local_path="files/cilium.sh",
            remote_path="/tmp/cilium.sh"
        )
        # time.sleep(10)
        command_command_resource = remote.Command(f"commandResource-{name}",
            connection=connection,
            create="sudo -u root -H sh /tmp/cilium.sh",
            update="sudo -u root -H sh /tmp/cilium.sh",
            opts=pulumi.ResourceOptions(depends_on=[copy_file_resource])

            # delete="string",
            # environment={
            #     "string": "string",
            # },
            # stdin="string",
            # triggers=["any"],
            # update="string"
        )