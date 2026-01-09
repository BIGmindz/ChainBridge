# ═══════════════════════════════════════════════════════════════════════════════
# PAC-OPS-P110: TERRAFORM OUTPUTS
# ═══════════════════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────────────────────
# VPC OUTPUTS
# ─────────────────────────────────────────────────────────────────────────────
output "vpc_id" {
  description = "ID of the Sovereign VPC"
  value       = aws_vpc.sovereign_cloud.id
}

output "vpc_cidr" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.sovereign_cloud.cidr_block
}

# ─────────────────────────────────────────────────────────────────────────────
# SUBNET OUTPUTS
# ─────────────────────────────────────────────────────────────────────────────
output "public_subnet_id" {
  description = "ID of the public subnet"
  value       = aws_subnet.public.id
}

# ─────────────────────────────────────────────────────────────────────────────
# SECURITY OUTPUTS
# ─────────────────────────────────────────────────────────────────────────────
output "security_group_id" {
  description = "ID of the Kernel security group"
  value       = aws_security_group.kernel_sg.id
}

# ─────────────────────────────────────────────────────────────────────────────
# INSTANCE OUTPUTS
# ─────────────────────────────────────────────────────────────────────────────
output "kernel_instance_id" {
  description = "ID of the Kernel EC2 instance"
  value       = aws_instance.kernel_node.id
}

output "kernel_public_ip" {
  description = "Public IP address of the Kernel node"
  value       = aws_instance.kernel_node.public_ip
}

output "kernel_public_dns" {
  description = "Public DNS name of the Kernel node"
  value       = aws_instance.kernel_node.public_dns
}

# ─────────────────────────────────────────────────────────────────────────────
# CONNECTION OUTPUTS
# ─────────────────────────────────────────────────────────────────────────────
output "api_endpoint" {
  description = "ChainBridge GaaS API endpoint"
  value       = "http://${aws_instance.kernel_node.public_ip}:3000"
}

output "health_check_url" {
  description = "Health check URL"
  value       = "http://${aws_instance.kernel_node.public_ip}:3000/health"
}

output "ssh_command" {
  description = "SSH command to connect to the Kernel node"
  value       = "ssh -i ~/.ssh/${var.key_pair_name}.pem ubuntu@${aws_instance.kernel_node.public_ip}"
}
