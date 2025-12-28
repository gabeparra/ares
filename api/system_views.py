from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from .auth import require_auth
import os
import subprocess
import json


@require_http_methods(["GET"])
@require_auth
def logs_tail(request):
    """
    Tail logs for:
      - source=backend   (tails /app/logs/backend.log)
      - source=docker    (tails docker logs for a limited set of containers)
    """
    source = (request.GET.get("source") or "backend").strip()
    try:
        lines = int(request.GET.get("lines", 400))
    except Exception:
        lines = 400
    lines = max(10, min(5000, lines))

    def make_response(data):
        response = JsonResponse(data)
        response["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response["Pragma"] = "no-cache"
        response["Expires"] = "0"
        return response

    if source == "backend":
        log_path = getattr(settings, "BACKEND_LOG_FILE", None)
        if not log_path:
            log_path = os.path.join(str(settings.BASE_DIR), "logs", "backend.log")
        try:
            with open(str(log_path), "r", encoding="utf-8", errors="replace") as f:
                data = f.read().splitlines()
            tail = data[-lines:]
            return make_response({"source": "backend", "lines": tail})
        except FileNotFoundError:
            return JsonResponse(
                {"source": "backend", "error": f"Log file not found: {log_path}", "lines": []},
                status=404,
            )
        except Exception as e:
            return JsonResponse({"source": "backend", "error": str(e), "lines": []}, status=500)

    if source == "docker":
        container = (request.GET.get("container") or "").strip()
        allowed = {
            "ares-backend-1",
            "ares-frontend_dev-1",
            "ares-frontend",
        }
        if container not in allowed:
            return JsonResponse(
                {
                    "source": "docker",
                    "error": f"container must be one of: {sorted(list(allowed))}",
                    "lines": [],
                },
                status=400,
            )

        try:
            # Requires docker CLI + /var/run/docker.sock mounted into this container.
            p = subprocess.run(
                ["docker", "logs", "--tail", str(lines), container],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            out = (p.stdout or "") + (("\n" + p.stderr) if p.stderr else "")
            return make_response(
                {
                    "source": "docker",
                    "container": container,
                    "exit_code": p.returncode,
                    "lines": out.splitlines()[-lines:],
                }
            )
        except FileNotFoundError:
            return JsonResponse(
                {
                    "source": "docker",
                    "container": container,
                    "error": "docker CLI not available in backend container",
                    "lines": [],
                },
                status=500,
            )
        except Exception as e:
            return JsonResponse(
                {"source": "docker", "container": container, "error": str(e), "lines": []},
                status=500,
            )

    return JsonResponse({"error": "invalid source", "source": source, "lines": []}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
@require_auth
def restart_service(request):
    """
    Restart a Docker service (backend or frontend).
    POST /api/v1/services/restart
    Body: {"service": "backend" | "frontend"}
    """
    try:
        data = json.loads(request.body)
        service = data.get("service", "").strip()
        
        allowed_services = {
            "backend": "ares-backend-1",
            "frontend": "ares-frontend_dev-1",
        }
        
        if service not in allowed_services:
            return JsonResponse({
                "error": f"Invalid service. Must be one of: {list(allowed_services.keys())}"
            }, status=400)
        
        container_name = allowed_services[service]
        
        # Start the restart in the background using a delayed command
        # This allows the response to be sent before the container restarts
        # Use 'sleep 1 && docker restart' to give time for response to be sent
        subprocess.Popen(
            ["sh", "-c", f"sleep 2 && docker restart {container_name}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        
        return JsonResponse({
            "success": True,
            "message": f"Service '{service}' will restart in 2 seconds",
            "container": container_name,
        })
            
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except FileNotFoundError:
        return JsonResponse({"error": "Docker CLI not available"}, status=500)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

