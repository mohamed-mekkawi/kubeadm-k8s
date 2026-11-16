provider "aws" {
  region  = var.region
  profile = var.aws_profile
}

locals {
  master = var.nodes[0]
}

data "aws_vpc" "default" {
  default = true
}

data "aws_ssm_parameter" "ubuntu" {
  name = "/aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id"
}

resource "aws_security_group" "k8s" {
  name   = "k8s-lab"
  vpc_id = data.aws_vpc.default.id

  # كل الترافيك بين الـ nodes نفسها
  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    self      = true
  }

  # من جهازك انت بس: SSH + API server + NodePorts
  dynamic "ingress" {
    for_each = {
      ssh      = [22, 22]
      api      = [6443, 6443]
      nodeport = [30000, 32767]
    }
    content {
      from_port   = ingress.value[0]
      to_port     = ingress.value[1]
      protocol    = "tcp"
      cidr_blocks = compact([var.my_ip, var.runner_ip])
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "node" {
  for_each               = toset(var.nodes)
  ami                    = data.aws_ssm_parameter.ubuntu.value
  instance_type          = var.instance_type
  key_name               = var.key_name
  vpc_security_group_ids = [aws_security_group.k8s.id]

  root_block_device {
    volume_size = 20
  }

  tags = {
    Name = "k8s-${each.key}"
  }
}

