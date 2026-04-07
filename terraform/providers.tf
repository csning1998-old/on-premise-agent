
terraform {
  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "5.19.0-beta.2"
    }
  }
}

provider "cloudflare" {
  api_token = var.cloudflare.api_token
}
