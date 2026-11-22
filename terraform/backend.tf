terraform {
  backend "s3" {
    bucket       = "kubeadm-k8s-tfstate-036253061913-eu-west-1"
    key          = "kubeadm/terraform.tfstate"
    region       = "eu-west-1"
    encrypt      = true
    use_lockfile = true
  }
}