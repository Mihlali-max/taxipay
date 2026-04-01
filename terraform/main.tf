terraform {
  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.44"
    }
  }
}

# Variables
variable "hcloud_token" {
  sensitive = true
  description = "Hetzner Cloud API token"
}

variable "ssh_key_name" {
  default = "fareflow-key"
}

variable "server_name" {
  default = "fareflow-prod"
}

# Provider - Hetzner Cloud (cheapest good VPS ~$5/month)
provider "hcloud" {
  token = var.hcloud_token
}

# SSH Key
resource "hcloud_ssh_key" "fareflow" {
  name       = var.ssh_key_name
  public_key = file("~/.ssh/fareflow_key.pub")
}

# Firewall
resource "hcloud_firewall" "fareflow" {
  name = "fareflow-firewall"

  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "22"
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "80"
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "443"
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  rule {
    direction  = "out"
    protocol   = "tcp"
    port       = "any"
    destination_ips = ["0.0.0.0/0", "::/0"]
  }

  rule {
    direction  = "out"
    protocol   = "udp"
    port       = "any"
    destination_ips = ["0.0.0.0/0", "::/0"]
  }
}

# Server
resource "hcloud_server" "fareflow" {
  name        = var.server_name
  image       = "ubuntu-22.04"
  server_type = "cx22"  # 2 vCPU, 4GB RAM, ~$6/month
  location    = "hel1"  # Helsinki - closest to SA with good latency
  ssh_keys    = [hcloud_ssh_key.fareflow.id]
  firewall_ids = [hcloud_firewall.fareflow.id]

  user_data = <<-EOT
    #!/bin/bash
    apt-get update
    apt-get install -y docker.io docker-compose-plugin
    systemctl enable docker
    systemctl start docker
    usermod -aG docker ubuntu
  EOT

  labels = {
    app = "fareflow"
    env = "production"
  }
}

# Floating IP for zero-downtime deploys
resource "hcloud_floating_ip" "fareflow" {
  name      = "fareflow-ip"
  type      = "ipv4"
  home_location = "hel1"
}

resource "hcloud_floating_ip_assignment" "fareflow" {
  floating_ip_id = hcloud_floating_ip.fareflow.id
  server_id      = hcloud_server.fareflow.id
}

# Outputs
output "server_ip" {
  value = hcloud_server.fareflow.ipv4_address
}

output "floating_ip" {
  value = hcloud_floating_ip.fareflow.ip_address
}
