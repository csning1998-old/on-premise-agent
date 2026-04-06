
# Project Identification
variable "project_info" {
  description = "Project metadata for local and cloudflare resource labeling"
  type = object({
    name      = string
    base_path = string
  })
}

# Container Images
variable "container_images" {
  description = "Container images for the application services"
  type = object({
    ollama  = string
    webui   = string
    searxng = string
  })
}

# Sensitive Credentials
variable "cloudflare" {
  description = "Cloudflare security credentials"
  type = object({
    api_token = string
  })
  sensitive = true
}

# Service Configurations
variable "open_web_ui" {
  description = "Open WebUI frontend configurations"
  type = object({
    port              = number
    enable_openai_api = bool
    ollama_base_url   = string
    secret_key        = string
  })
  sensitive = true
}

variable "searxng" {
  description = "SearXNG search engine configurations"
  type = object({
    port = number
  })
}
