# ═══════════════════════════════════════════════════════════════════════════════
# PAC-OPS-P110: EXAMPLE TERRAFORM VARIABLES
# ═══════════════════════════════════════════════════════════════════════════════
# Copy this file to terraform.tfvars and customize for your deployment.
# NEVER commit terraform.tfvars to git!
# ═══════════════════════════════════════════════════════════════════════════════

# Project Settings
project_name = "ChainBridge"
environment  = "alpha"

# AWS Settings
aws_region = "us-east-1"

# Network Settings
vpc_cidr           = "10.0.0.0/16"
public_subnet_cidr = "10.0.1.0/24"

# Security Settings (RESTRICT IN PRODUCTION!)
ssh_allowed_cidrs = ["YOUR_IP_ADDRESS/32"]  # Replace with your IP

# Compute Settings
ami_id        = "ami-0c7217cdde317cfec"  # Ubuntu 22.04 LTS (us-east-1)
instance_type = "t3.micro"
key_pair_name = "chainbridge-alpha"       # Must create this in AWS first

# Application Settings
docker_image = "chainbridge:v1.0.0-BETA"
