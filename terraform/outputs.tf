output "public_ips" {
  value = { for k, v in aws_instance.node : k => v.public_ip }
}

output "master_private_ip" {
  value = aws_instance.node[local.master].private_ip
}

output "ssh_master" {
  value = "ssh -i ${var.key_path} ubuntu@${aws_instance.node[local.master].public_ip}"
}