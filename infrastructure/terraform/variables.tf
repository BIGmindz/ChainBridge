# ═══════════════════════════════════════════════════════════════════════════════
# PAC-OPS-P110: TERRAFORM VARIABLES
# ═══════════════════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────────────────────
# PROJECT METADATA
# ─────────────────────────────────────────────────────────────────────────────
variable "project_name" {
  description = "Project name for resource tagging"
  type        = string
  default     = "ChainBridge"
}

variable "environment" {
  description = "Deployment environment (alpha, beta, prod)"
  type        = string
  default     = "alpha"
}

# ─────────────────────────────────────────────────────────────────────────────
# AWS CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

# ─────────────────────────────────────────────────────────────────────────────
# NETWORK CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR block for the public subnet"
  type        = string
  default     = "10.0.1.0/24"
}

# ─────────────────────────────────────────────────────────────────────────────
# SECURITY CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
variable "ssh_allowed_cidrs" {
  description = "CIDR blocks allowed for SSH access (restrict in production!)"
  type        = list(string)
  default     = ["0.0.0.0/0"]  # WARNING: Open for Alpha, restrict for Prod
}

# ─────────────────────────────────────────────────────────────────────────────
# COMPUTE CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
variable "ami_id" {
  description = "AMI ID for EC2 instance (Ubuntu 22.04 LTS)"
  type        = string
  default     = "ami-0c7217cdde317cfec"  # Ubuntu 22.04 LTS us-east-1
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"  # Free tier eligible, sufficient for Alpha
}

variable "key_pair_name" {
  description = "Name of the SSH key pair for EC2 access"
  type        = string
  default     = "chainbridge-alpha"  # Must exist in AWS
}

# ─────────────────────────────────────────────────────────────────────────────
# APPLICATION CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
variable "docker_image" {
  description = "Docker image to deploy"
  type        = string
  default     = "chainbridge:v1.0.0-BETA"
}
