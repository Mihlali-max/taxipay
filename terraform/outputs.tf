output "ssh_command" {
  value = "ssh ubuntu@${hcloud_server.fareflow.ipv4_address}"
}

output "app_url" {
  value = "http://${hcloud_floating_ip.fareflow.ip_address}"
}
