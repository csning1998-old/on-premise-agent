
# Project Identification
variable "project_name" {
  description = "Project name for local and cloudflare resource labeling"
  type        = string
}

# Path Configuration
variable "base_data_path" {
  description = "Base absolute path for persistent data volumes"
  type        = string
}

# Container Images
variable "ollama_image" {
  description = "Image for Ollama inference service"
  type        = string
}

variable "webui_image" {
  description = "Image for Open WebUI frontend"
  type        = string
}

variable "searxng_image" {
  description = "Image for SearXNG engine"
  type        = string
}

# Sensitive Credentials
variable "cloudflare_api_token" {
  description = "Cloudflare API Token for DNS and Tunnel management"
  type        = string
  sensitive   = true
}

variable "webui_secret_key" {
  description = "Secret key for Open WebUI sessions"
  type        = string
  sensitive   = true
}

# WebUI Configurations
variable "webui_enable_openai_api" {
  description = "Toggle for OpenAI API support in WebUI"
  type        = bool
}

variable "webui_ollama_base_url" {
  description = "Base URL for Ollama service within the network"
  type        = string
}

variable "webui_port" {
  description = "External port for Open WebUI"
  type        = number
}

variable "searxng_port" {
  description = "External port for SearXNG"
  type        = number
}
