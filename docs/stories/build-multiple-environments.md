User Story 1: Provision Separate VM Environments
User Story & Description: As a homelab administrator, I want to provision two distinct sets of virtual machines on Rackspace Spot, so that I can create separate, isolated environments for my production and lab clusters.

In-Scope:

Using Terraform to provision VMs on Rackspace Spot.

Allocating a dedicated set of VMs for a "prod" environment (at least 3 control planes, plus workers).

Allocating a dedicated set of VMs for a "lab" environment (at least 3 control planes, plus workers).

Configuring separate network segments (VLANs or subnets) for each environment.

Out-of-Scope:

Installing Kubernetes (K3s) or any applications.

Configuring the operating system (Kairos).

Setting up DNS or load balancers.

Acceptance Criteria:

Given I have access to the Rackspace cloud environment,

When I run the Terraform plan,

Then it should show the creation of at least 6 new VMs (3 for prod control plane, 3 for lab control plane) plus any worker nodes.

Given the Terraform apply is complete,

When I check the Rackspace console,

Then I should see all the specified VMs running.

Given the VMs are running,

When I inspect the networking configuration,

Then the "prod" VMs must be in a different subnet from the "lab" VMs.

Definition of Done:

[ ] Terraform code for provisioning both environments is committed to the repository.

[ ] All VMs for both "prod" and "lab" environments are successfully created and running in Rackspace.

[ ] Network segmentation between the two environments is verified.

[ ] Documentation for the VM and network layout is created or updated.