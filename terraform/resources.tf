
# Image management (Parameterized)
resource "docker_image" "ollama" {
  name = var.container_images.ollama
}

resource "docker_image" "open_webui" {
  name = var.container_images.webui
}

resource "docker_image" "searxng" {
  name = var.container_images.searxng
}

# Network for service communication
resource "docker_network" "rag_network" {
  name        = "rag-network"
  ipam_driver = "default"

  lifecycle {
    ignore_changes = [ipam_options]
  }
}

# Container Services

# 1. Ollama Inference Node
resource "docker_container" "ollama" {
  name          = "ollama"
  image         = docker_image.ollama.image_id
  security_opts = ["no-new-privileges:true"]
  pid_mode      = "private"
  restart       = "unless-stopped"

  networks_advanced {
    name = docker_network.rag_network.name
  }

  volumes {
    container_path  = "/root/.ollama"
    host_path       = abspath("${path.root}/../ollama_data")
    selinux_relabel = "Z"
  }

  capabilities {
    drop = ["ALL"]
  }

  lifecycle {
    ignore_changes = [ulimit, security_opts, pid_mode, capabilities]
  }
}

# 2. Open WebUI Frontend
resource "docker_container" "webui" {
  depends_on    = [docker_container.ollama]
  name          = "open-webui"
  image         = docker_image.open_webui.image_id
  security_opts = ["no-new-privileges:true"]
  pid_mode      = "private"
  restart       = "unless-stopped"

  env = [
    "OLLAMA_BASE_URL=${var.open_web_ui.ollama_base_url}",
    "WEBUI_SECRET_KEY=${var.open_web_ui.secret_key}",
    "ENABLE_OPENAI_API=${var.open_web_ui.enable_openai_api}",
    "ENABLE_RAG_WEB_SEARCH=${var.open_web_ui.enable_rag_web_search}",
    "RAG_WEB_SEARCH_ENGINE=searxng",
    "SEARXNG_QUERY_URL=${var.open_web_ui.searxng_query_url}"
  ]

  networks_advanced {
    name = docker_network.rag_network.name
  }

  ports {
    internal = 8080
    external = var.open_web_ui.port
  }

  volumes {
    container_path  = "/app/backend/data"
    host_path       = abspath("${path.root}/../open-webui_data")
    selinux_relabel = "Z"
  }

  capabilities {
    drop = ["ALL"]
  }

  lifecycle {
    ignore_changes = [ulimit, security_opts, pid_mode, capabilities]
  }
}

# 3. SearXNG Search Engine
resource "docker_container" "searxng" {
  name          = "searxng"
  image         = docker_image.searxng.image_id
  security_opts = ["no-new-privileges:true"]
  pid_mode      = "private"
  restart       = "unless-stopped"

  env = [
    "BASE_URL=${var.searxng.base_url}",
    "SEARXNG_LIMITER=false"
  ]

  networks_advanced {
    name = docker_network.rag_network.name
  }

  ports {
    internal = 8080
    external = var.searxng.port
  }

  volumes {
    container_path  = "/etc/searxng"
    host_path       = abspath("${path.root}/../searxng_data")
    read_only       = false
    selinux_relabel = "Z"
  }

  capabilities {
    drop = ["ALL"]
  }

  lifecycle {
    ignore_changes = [ulimit, security_opts, pid_mode, capabilities]
  }
}
