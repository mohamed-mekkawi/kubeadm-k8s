variable "region" {
  description = "AWS region"
  type        = string
}

variable "aws_profile" {
  type = string
}

variable "key_name" {
  type = string
}
variable "key_path" {
  type = string
}


variable "my_ip" {
  type = string
}

variable "instance_type" {
  type = string
}

variable "nodes" {
  type = list(string)
}