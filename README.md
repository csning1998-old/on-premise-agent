# Open WebUI + Ollama RAG

## Section 1. Configure Environment

### Step A. NVIDIA GPU Container Device Interface

To allow Podman to correctly identify and invoke NVIDIA GPUs, a CDI (Container Device Interface) specification file must be generated.

- **Generate CDI configuration file:**

    It is recommended to use a system-wide path to ensure complete permissions.

    ```zsh
    sudo mkdir -p /etc/cdi
    sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml --device-name-strategy=type-index
    ```

- **Verify device list:**

    Confirm that the output includes `nvidia.com/gpu=all`.

    ```zsh
    nvidia-ctk cdi list
    ```

- **Smoke Test:**

    Ensure that GPU information can be correctly read inside the container.

    ```zsh
    podman run --rm --device nvidia.com/gpu=all fedora nvidia-smi
    ```

### Step B. SELinux Security Policy Configuration

Fedora's default SELinux policy restricts container access to hardware devices and specific system calls; these must be manually permitted.

- **Enable device usage permissions:**

    ```zsh
    sudo setsebool -P container_use_devices true
    sudo setsebool -P container_manage_cgroup true
    ```

- **Reset device node security:**
  To prevent terminal access errors that may be caused by the Rootless network driver (pasta).

    ```zsh
    sudo restorecon -v /dev/ptmx
    ```

### Step C. Security Keys and Environment Variables Preparation

Before starting the service, an encryption key for Open WebUI must be generated.

- **Generate a random Base64 key:**

    ```zsh
    openssl rand -base64 32
    ```

    Fill the generated string into the `WEBUI_SECRET_KEY` variable in the `.env` file.

### Step D. Volume Permissions and UID Mapping Handling

In Rootless mode, there is a mapping relationship between the host user and the `root` (UID 0) inside the container; `podman unshare` must be used to correct directory ownership.

- **Directory initialization and permission transfer:**
    1. Create data storage directories
    2. Map directory ownership to the container's root (0:0)
    3. Grant appropriate read, write, and execute permissions

    ```zsh
    mkdir -p ./ollama_data ./open-webui_data
    podman unshare chown -R 0:0 ./ollama_data ./open-webui_data
    chmod -R 775 ./ollama_data ./open-webui_data
    ```

### Step E. Service Startup and Verification

Use Podman Compose to start the integrated services and ensure SELinux labels are correct.

- **Start services:**

    ```zsh
    podman-compose up -d
    ```

- **Check Ollama model list and permissions:**

    If this step does not report `permission denied`, the permission configuration was successful.

    ```zsh
    podman exec -it ollama ollama list
    ```

- **View real-time logs:**

    ```zsh
    podman-compose logs -f
    ```

## Section 2. Troubleshooting

### A. Permission Denied (`mkdir /root/.ollama/models`)

Usually caused by a missing `:Z,U` label in `compose.yaml`, or failing to run `podman unshare`. Please ensure the mount point is configured as `- ./ollama_data:/root/.ollama:Z,U`.

### B. Unresolvable CDI Device

Please confirm whether the `/etc/cdi/nvidia.yaml` file contains the correct device name and ensure the file has global read permissions (`chmod a+r`).

```zsh
podman unshare chown -R 0:0 ./ollama_data ./open-webui_data
chmod -R 775 ./ollama_data ./open-webui_data
```
