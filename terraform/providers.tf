
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
  host = var.project_info.docker_host
}

provider "cloudflare" {
  api_token = var.cloudflare.api_token
}
