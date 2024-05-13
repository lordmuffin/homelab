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

def bootstrap(node_list):
    for i in node_list:
        name = i["name"]
        ip = i["ip"]
        print(i["ip"])
        connection = remote.ConnectionArgs(
            host=ip,
            user="ubuntu",
            # password="ubuntu"
            private_key=i["ssh_priv_key"],
            private_key_password=None,
        )
        copy_file_resource = remote.CopyFile(f"copyFileResource-{name}-{ip}",
            connection=connection,
            local_path="files/bootstrap.sh",
            remote_path="/tmp/bootstrap.sh"
        )
        # time.sleep(10)
        command_command_resource = remote.Command(f"commandResource-{name}",
            connection=connection,
            create="sh /tmp/bootstrap.sh",
            update="sh /tmp/bootstrap.sh",
            opts=pulumi.ResourceOptions(depends_on=[copy_file_resource])

            # delete="string",
            # environment={
            #     "string": "string",
            # },
            # stdin="string",
            # triggers=["any"],
            # update="string"
        )