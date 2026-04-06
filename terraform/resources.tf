
# Network for service communication
resource "docker_network" "rag_network" {
  name = "rag-network"
}

# Image management (Parameterized)
resource "docker_image" "ollama" {
  name = var.ollama_image
}

resource "docker_image" "open_webui" {
  name = var.webui_image
}

resource "docker_image" "searxng" {
  name = var.searxng_image
}

# Container Services

# Ollama Inference Node
resource "docker_container" "ollama" {
  name  = "ollama"
  image = docker_image.ollama.image_id
  networks_advanced {
    name = docker_network.rag_network.name
  }
  volumes {
    container_path  = "/root/.ollama"
    host_path       = "${var.base_data_path}/ollama_data"
    selinux_relabel = "Z"
  }
  security_opts = ["no-new-privileges:true"]
  capabilities {
    drop = ["ALL"]
  }
  restart = "unless-stopped"
}

# Open WebUI Frontend
resource "docker_container" "webui" {
  name  = "open-webui"
  image = docker_image.open_webui.image_id
  networks_advanced {
    name = docker_network.rag_network.name
  }
  ports {
    internal = 8080
    external = var.webui_port
  }
  env = [
    "OLLAMA_BASE_URL=${var.webui_ollama_base_url}",
    "WEBUI_SECRET_KEY=${var.webui_secret_key}",
    "ENABLE_OPENAI_API=${var.webui_enable_openai_api}"
  ]
  volumes {
    container_path  = "/app/backend/data"
    host_path       = "${var.base_data_path}/open-webui_data"
    selinux_relabel = "Z"
  }
  security_opts = ["no-new-privileges:true"]
  capabilities {
    drop = ["ALL"]
  }
  restart    = "unless-stopped"
  depends_on = [docker_container.ollama]
}

# SearXNG Search Engine
resource "docker_container" "searxng" {
  name  = "searxng"
  image = docker_image.searxng.image_id
  networks_advanced {
    name = docker_network.rag_network.name
  }
  ports {
    internal = 8080
    external = var.searxng_port
  }
  env = [
    "BASE_URL=http://searxng:8080/",
    "SEARXNG_LIMITER=false"
  ]
  volumes {
    container_path  = "/etc/searxng"
    host_path       = "${var.base_data_path}/searxng_data"
    read_only       = false
    selinux_relabel = "Z"
  }
  security_opts = ["no-new-privileges:true"]
  capabilities {
    drop = ["ALL"]
  }
  restart = "unless-stopped"
}
