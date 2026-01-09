# ═══════════════════════════════════════════════════════════════════════════════
# PAC-OPS-P110-AWS-INFRA: SOVEREIGN CLOUD INFRASTRUCTURE
# ═══════════════════════════════════════════════════════════════════════════════
# CONSTITUTIONAL INVARIANTS:
#   - Control > Autonomy: If it isn't in Terraform, it doesn't exist.
#   - Fail-Closed: Security Groups deny all by default.
#   - Sovereignty: Custom VPC, no shared infrastructure.
# ═══════════════════════════════════════════════════════════════════════════════

terraform {
  required_version = ">= 1.0.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# PROVIDER CONFIGURATION
# Credentials via environment: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
# ─────────────────────────────────────────────────────────────────────────────
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "ChainBridge"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Version     = "v1.0.0-BETA"
    }
  }
}

# ═══════════════════════════════════════════════════════════════════════════════
# 1. THE MOAT (VPC)
# A Sovereign Virtual Private Cloud - complete network isolation
# ═══════════════════════════════════════════════════════════════════════════════
resource "aws_vpc" "sovereign_cloud" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.project_name}-Sovereign-VPC"
  }
}

# ═══════════════════════════════════════════════════════════════════════════════
# 2. THE GATE (Internet Gateway)
# Single point of entry/exit for the VPC
# ═══════════════════════════════════════════════════════════════════════════════
resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.sovereign_cloud.id

  tags = {
    Name = "${var.project_name}-IGW"
  }
}

# ═══════════════════════════════════════════════════════════════════════════════
# 3. THE PATH (Public Subnet)
# Where the Kernel Node lives - publicly addressable
# ═══════════════════════════════════════════════════════════════════════════════
resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.sovereign_cloud.id
  cidr_block              = var.public_subnet_cidr
  availability_zone       = "${var.aws_region}a"
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-Public-Subnet"
    Type = "Public"
  }
}

# ═══════════════════════════════════════════════════════════════════════════════
# 4. THE ROUTE (Route Table)
# Directs traffic: Internal stays internal, external goes through IGW
# ═══════════════════════════════════════════════════════════════════════════════
resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.sovereign_cloud.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }

  tags = {
    Name = "${var.project_name}-Public-RT"
  }
}

resource "aws_route_table_association" "public_rta" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public_rt.id
}

# ═══════════════════════════════════════════════════════════════════════════════
# 5. THE WALL (Security Group)
# FAIL-CLOSED: Deny all by default, explicit allow only
# ═══════════════════════════════════════════════════════════════════════════════
resource "aws_security_group" "kernel_sg" {
  name        = "${var.project_name}-kernel-sg"
  description = "Strict ingress for ChainBridge GaaS Kernel"
  vpc_id      = aws_vpc.sovereign_cloud.id

  # ─────────────────────────────────────────────────────────────────────────────
  # INGRESS: API Access (The Gasket)
  # Port 3000 is the ONLY door for GaaS traffic
  # ─────────────────────────────────────────────────────────────────────────────
  ingress {
    description = "GaaS API (Port 3000)"
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Public API
  }

  # ─────────────────────────────────────────────────────────────────────────────
  # INGRESS: SSH Access (Sovereign Admin Only)
  # TODO: In production, restrict to Admin IP (var.admin_cidr)
  # ─────────────────────────────────────────────────────────────────────────────
  ingress {
    description = "SSH Admin Access"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.ssh_allowed_cidrs
  }

  # ─────────────────────────────────────────────────────────────────────────────
  # EGRESS: Allow outbound for updates and Docker pulls
  # ─────────────────────────────────────────────────────────────────────────────
  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-Kernel-SG"
  }
}

# ═══════════════════════════════════════════════════════════════════════════════
# 6. THE THRONE (EC2 Instance)
# The Kernel Node - runs the ChainBridge Docker container
# ═══════════════════════════════════════════════════════════════════════════════
resource "aws_instance" "kernel_node" {
  ami                    = var.ami_id
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.kernel_sg.id]
  key_name               = var.key_pair_name

  # ─────────────────────────────────────────────────────────────────────────────
  # BOOT SCRIPT (User Data)
  # Installs Docker and runs the ChainBridge Kernel container
  # ─────────────────────────────────────────────────────────────────────────────
  user_data = <<-EOF
              #!/bin/bash
              set -e
              
              # System Update
              apt-get update -y
              apt-get upgrade -y
              
              # Install Docker
              apt-get install -y docker.io
              systemctl start docker
              systemctl enable docker
              
              # Add ubuntu user to docker group
              usermod -aG docker ubuntu
              
              # Create logs directory
              mkdir -p /var/log/chainbridge
              
              # Pull and Run ChainBridge Kernel
              # NOTE: For Alpha, assumes local/public registry
              # In production, authenticate to ECR:
              # aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin <account>.dkr.ecr.${var.aws_region}.amazonaws.com
              
              docker run -d \
                -p 3000:3000 \
                --restart always \
                --name chainbridge-kernel \
                -v /var/log/chainbridge:/logs \
                ${var.docker_image}
              
              # Health check marker
              echo "ChainBridge Kernel v1.0.0-BETA deployed at $(date)" > /var/log/chainbridge/deploy.log
              EOF

  root_block_device {
    volume_size           = 20
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
  }

  tags = {
    Name = "${var.project_name}-Kernel-Node-01"
    Role = "GaaS-Kernel"
  }
}
