"""
Luqi-AI Lab Sandbox Engine
Spins up isolated, resource-capped containers per student lab session.
Requires the Docker daemon running on the host (or DOCKER_HOST set).
"""
import os
import docker
from typing import Dict, Any

# Use real, pullable images. The Kali image is large (~4GB) - pull once on the host:
#   docker pull kalilinux/kali-rolling
IMAGE_MAP = {
    "software_dev": "luqi-lab-base:latest",  # build from lab/Dockerfile
    "networking": "alpine:latest",
    "cybersecurity": "kalilinux/kali-rolling",
}


class LabSandboxManager:
    def __init__(self):
        self.client = docker.from_env()

    def provision_student_environment(self, student_id: str, track: str) -> Dict[str, Any]:
        image = IMAGE_MAP.get(track, "alpine:latest")
        container_name = f"luqi-lab-{student_id}-{os.urandom(4).hex()}"

        # Ceiling enforcement: refuse to spawn beyond the configured sandbox cap.
        # Without this check, MAX_SANDBOX_CONTAINERS was a config value with no teeth.
        max_containers = int(os.getenv("MAX_SANDBOX_CONTAINERS", "500"))
        try:
            running = self.client.containers.list(filters={"name": "luqi-lab-"})
            if len(running) >= max_containers:
                return {
                    "status": "failed",
                    "error": f"Sandbox ceiling reached ({max_containers} active). Retry shortly.",
                    "environment_ready": False,
                    "retry_after_seconds": 30,
                }
        except Exception:
            pass  # ceiling check is best-effort; never block on a monitoring failure

        try:
            container = self.client.containers.run(
                image=image,
                name=container_name,
                command="sleep 3600",          # 1-hour lab session
                detach=True,
                mem_limit="512m",
                nano_cpus=500000000,           # max 0.5 CPU cores
                network_mode="bridge",
                cap_drop=["ALL"],              # drop all root capabilities
                security_opt=["no-new-privileges"],
            )
            return {
                "status": "success",
                "container_id": container.short_id,
                "container_name": container_name,
                "environment_ready": True,
            }
        except Exception as e:
            return {"status": "failed", "error": str(e), "environment_ready": False}

    def execute_student_command(self, container_name: str, command: str) -> str:
        """Runs a student command in the sandbox and returns stdout/stderr.
        Executes as the non-root 'luqistudent' user defined in the Luqi-AI
        Dockerfile; falls back to 'nobody' for stock images (alpine, etc.)."""
        try:
            container = self.client.containers.get(container_name)
            try:
                exit_code, output = container.exec_run(cmd=command, user="luqistudent")
            except Exception:
                exit_code, output = container.exec_run(cmd=command, user="nobody")
            return output.decode("utf-8", errors="replace")
        except Exception as e:
            return f"Sandbox Runtime Error: {str(e)}"

    def destroy_environment(self, container_name: str) -> None:
        try:
            container = self.client.containers.get(container_name)
            container.remove(force=True)
        except Exception:
            pass  # already gone
