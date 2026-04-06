
terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "4.0.0"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "5.19.0-beta.2"
    }
  }
}

provider "docker" {
  host = "unix:///run/user/1000/podman/podman.sock"
}

provider "cloudflare" {
  api_token = var.cloudflare.api_token
}
