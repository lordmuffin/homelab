"""A Python Pulumi program"""
import os
import pulumi
import pulumi_proxmoxve as proxmoxve

class Provider:
   def __init__(self, endpoint, username, password, insecure):
        self.endpoint = endpoint,
        self.username = username,
        self.password = password,
        self.insecure = insecure

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


def create_vm(name, description, node_name, clone_vm_id, provider):
    vm_clone_spec=proxmoxve.vm.VirtualMachineCloneArgs(
        vm_id=clone_vm_id,  # template's vmId
        full=True,  # full clone, not linked clone
        datastore_id="local-lvm",  # template's datastore
        node_name=node_name,  # template's node name
    )
    vm_cpu_spec=proxmoxve.vm.VirtualMachineCpuArgs(
        cores=2,
        sockets=2,
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
            vlan_id=0,
        )
    ]
    vm_initialization_spec=proxmoxve.vm.VirtualMachineInitializationArgs(
        type="nocloud",  # 'nocloud' for linux,  'configdrive2' for windows
        interface="scsi1",
        datastore_id="local-lvm",
        dns=proxmoxve.vm.VirtualMachineInitializationDnsArgs(
            # dns servers,
            server="114.114.114.114,8.8.8.8",
        ),
        ip_configs=[
            proxmoxve.vm.VirtualMachineInitializationIpConfigArgs(
                ipv4=proxmoxve.vm.VirtualMachineInitializationIpConfigIpv4Args(
                    address="192.168.1.111/24",
                    gateway="192.168.1.1"
                )
            )
        ],
        upgrade = True,
        user_account=proxmoxve.vm.VirtualMachineInitializationUserAccountArgs(
            # set root's ssh key
            keys=ssh_pub_keys,
            password="change_me",  # needed when login from console
            username="ubuntu",
        )
    )
    vm_opts_spec=pulumi.ResourceOptions(
        provider=provider
    )

    vm_spec = VM(name=name, description=description, node_name=node_name, on_boot=False, reboot=True, started=True, clone=vm_clone_spec, cpu=vm_cpu_spec, memory=vm_memory_spec, operating_system=vm_operating_system_spec, agent=vm_agent_spec, disks=vm_disks_spec, network_devices=vm_network_devices_spec, initialization=vm_initialization_spec, opts=vm_opts_spec)

    vm = proxmoxve.vm.VirtualMachine(
        vm_spec.name,
        name=vm_spec.name,
        description=vm_spec.description,
        node_name=vm_spec.node_name,
        on_boot=vm_spec.on_boot,  # start the vm during system bootup
        reboot=vm_spec.reboot,  # reboot the vm after it was created successfully
        started=vm_spec.started,  # start the vm after it was created successfully
        clone=vm_spec.clone,
        cpu=vm_cpu_spec,
        memory=vm_memory_spec,
        operating_system=vm_operating_system_spec,
        agent=vm_agent_spec,
        disks=vm_disks_spec,
        network_devices=vm_network_devices_spec,
        initialization=vm_initialization_spec,
        opts=vm_opts_spec
    )

# Variables
ssh_pub_keys = ["ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEGoIpTIeC7Kby3lHyw2g2kTwkb3MHCDPCJKzHWa6uhe"]

# Providers
node_pve_router_provider = proxmoxve.Provider('node_pve_router_provider',
    endpoint="https://192.168.1.11:8006/",
    username=os.getenv("PROXMOX_VE_USERNAME"),
    password=os.getenv("PROXMOX_VE_PASSWORD"),
    insecure=True
)
node_pve_provider = proxmoxve.Provider('node_pve_provider',
    endpoint="https://192.168.1.13:8006/",
    username=os.getenv("PROXMOX_VE_USERNAME"),
    password=os.getenv("PROXMOX_VE_PASSWORD"),
    insecure=True
)
node_pve2_provider = proxmoxve.Provider('node_pve2_provider',
    endpoint="https://192.168.1.14:8006/",
    username=os.getenv("PROXMOX_VE_USERNAME"),
    password=os.getenv("PROXMOX_VE_PASSWORD"),
    insecure=True
)
node_pve_nas_01_provider = proxmoxve.Provider('node_pve_nas_01_provider',
    endpoint="https://192.168.1.15:8006/",
    username=os.getenv("PROXMOX_VE_USERNAME"),
    password=os.getenv("PROXMOX_VE_PASSWORD"),
    insecure=True
)

# Create VM's
# name, description, node_name, provider
create_vm("test-vm-1", "Ubuntu 22.04", "pve", 104, node_pve_provider)
create_vm("test-vm-2", "Ubuntu 22.04", "pve2", 102, node_pve2_provider)
create_vm("test-vm-3", "Ubuntu 22.04", "pve-nas-01", 115, node_pve_nas_01_provider)


# Export the VM's ID
# pulumi.export('vm_id', vm.vmid)
