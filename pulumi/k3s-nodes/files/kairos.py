import os
import pulumi
from pulumi import Output
import pulumi_proxmoxve as proxmoxve
from pulumi_command import local, remote

class Provider:
   def __init__(self, endpoint, username, password, insecure, node_name):
        self.endpoint = endpoint,
        self.username = username,
        self.password = password,
        self.insecure = insecure,
        self.node_name = node_name

class VM:
  def __init__(self, name, description, node_name, on_boot, reboot, started, clone, cpu, memory, operating_system, agent, disks, network_devices, initialization, opts):
    self.name = name
    self.description = description
    self.node_name = node_name
    self.on_boot = on_boot
    self.reboot = reboot
    self.started = started
    self.clone = clone
    self.cpu = cpu
    self.memory = memory
    self.operating_system = operating_system
    self.agent = agent
    self.disks = disks
    self.network_devices = network_devices
    self.initialization = initialization
    self.opts = opts


def create_vm(name, description, node_name, clone_vm_id, on_boot, reboot, started, ip, ssh_pub_keys, provider):
    hostpcis=proxmoxve.vm.VirtualMachineHostpciArgs(
        device="hostpci0",
        id=id,
    )
    vm_cpu_spec=proxmoxve.vm.VirtualMachineCpuArgs(
        cores=2,
        sockets=1,
        type="kvm64",  # set it to kvm64 for better vm migration
    )
    vm_memory_spec=proxmoxve.vm.VirtualMachineMemoryArgs(
        dedicated="4096"  # unit: MB
    )
    vm_operating_system_spec=proxmoxve.vm.VirtualMachineOperatingSystemArgs(
        type="l26"  # l26: linux2.6-linux5.x
    )
    vm_agent_spec=proxmoxve.vm.VirtualMachineAgentArgs(
        # please confirm you have qemu-guest-agent in your vm before enable this!
        # otherwise this may cause the vm to fail to shutdown/reboot!
        enabled=True,
        timeout="60s",  # timeout
    )
    vm_disks_spec=[
        proxmoxve.vm.VirtualMachineDiskArgs(
            interface="scsi0",
            datastore_id="local-lvm",
            size="40",  # unit: GB
            file_format="raw"
        )
    ]
    vm_network_devices_spec=[
        proxmoxve.vm.VirtualMachineNetworkDeviceArgs(
            enabled=True,
            bridge="vmbr0",
            model="virtio",
            vlan_id=10,
        )
    ]

    vm_opts_spec=pulumi.ResourceOptions(
        provider=provider
    )

    vm_spec = VM(name=name, description=description, node_name=node_name, on_boot=False, reboot=True, started=True, cpu=vm_cpu_spec, memory=vm_memory_spec, operating_system=vm_operating_system_spec, agent=vm_agent_spec, disks=vm_disks_spec, network_devices=vm_network_devices_spec, opts=vm_opts_spec)

    vm = proxmoxve.vm.VirtualMachine(
        vm_spec.name,
        name=vm_spec.name,
        description=vm_spec.description,
        node_name=vm_spec.node_name,
        on_boot=vm_spec.on_boot,  # start the vm during system bootup
        reboot=vm_spec.reboot,  # reboot the vm after it was created successfully
        started=vm_spec.started,  # start the vm after it was created successfully
        cpu=vm_spec.cpu,
        memory=vm_spec.memory,
        operating_system=vm_spec.operating_system,
        agent=vm_spec.agent,
        disks=vm_spec.disks,
        network_devices=vm_spec.network_devices,
        opts=vm_spec.opts
    )

    return vm

# Create VM's
# 
# Build Kairos nodes
def kairos_k3s_control_node(node_list):
    environment = "dev"
    name = "k3s-lab"
    qty = 3
    
    desc = "Kairos v1.28"

    count = 0
    for i in node_list:
        count += 1
        vm_name = f"{environment}-{name}-{count}"
        if count <= (qty + 1):
            vm = create_vm(vm_name, i["description"], i["node_name"], i["image_id"], i["on_boot"], i["reboot"], i["started"], i["ip"], i["ssh_pub_keys"], i["provider"])
