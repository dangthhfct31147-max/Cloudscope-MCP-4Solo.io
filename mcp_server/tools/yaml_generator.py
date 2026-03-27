"""Production-ready Kubernetes YAML generation for CloudScope."""

from __future__ import annotations

import json
from textwrap import dedent
from typing import Any


SUPPORTED_RESOURCE_TYPES = {
    "deployment",
    "service",
    "ingress",
    "configmap",
    "secret",
    "hpa",
    "pvc",
    "bundle",
}


def _labels(name: str) -> dict[str, str]:
    return {
        "app.kubernetes.io/name": name,
        "app.kubernetes.io/part-of": "cloudscope",
        "app.kubernetes.io/managed-by": "cloudscope",
    }


def _indent(block: str, spaces: int) -> str:
    prefix = " " * spaces
    return "\n".join(f"{prefix}{line}" if line else line for line in block.splitlines())


def _env_lines(env: dict[str, Any]) -> str:
    if not env:
        return "[]"
    lines = []
    for key, value in env.items():
        lines.append(f"- name: {key}")
        lines.append(f"  value: {json.dumps(str(value))}")
    return "\n".join(lines)


def _config_data_lines(data: dict[str, Any]) -> str:
    lines = []
    for key, value in data.items():
        lines.append(f"{key}: {json.dumps(str(value))}")
    return "\n".join(lines)


def _string_data_lines(data: dict[str, Any]) -> str:
    lines = []
    for key, value in data.items():
        lines.append(f"{key}: {json.dumps(str(value))}")
    return "\n".join(lines)


def _normalize_options(options: dict[str, Any] | None) -> dict[str, Any]:
    opts = dict(options or {})
    opts.setdefault("image", "ghcr.io/cloudscope/demo-app:1.0.0")
    opts.setdefault("replicas", 2)
    opts.setdefault("port", 8080)
    opts.setdefault("service_port", 80)
    opts.setdefault("host", "cloudscope.local")
    opts.setdefault("path", "/")
    opts.setdefault("cpu_request", "250m")
    opts.setdefault("memory_request", "256Mi")
    opts.setdefault("cpu_limit", "500m")
    opts.setdefault("memory_limit", "512Mi")
    opts.setdefault("storage_size", "10Gi")
    opts.setdefault("storage_class_name", "standard")
    opts.setdefault("access_modes", ["ReadWriteOnce"])
    opts.setdefault("min_replicas", 2)
    opts.setdefault("max_replicas", 5)
    opts.setdefault("target_cpu_utilization", 70)
    opts.setdefault("config_data", {"APP_MODE": "production", "LOG_LEVEL": "info"})
    opts.setdefault("secret_data", {"API_KEY": "replace-me", "TOKEN": "replace-me"})
    opts.setdefault("env", {"PORT": opts["port"], "APP_ENV": "production"})
    return opts


def _deployment_yaml(name: str, namespace: str, options: dict[str, Any]) -> str:
    labels = _labels(name)
    config_map_name = options.get("config_map_name")
    lines = [
        "# Deployment keeps the application self-healing and scalable.",
        "apiVersion: apps/v1",
        "kind: Deployment",
        "metadata:",
        f"  name: {name}",
        f"  namespace: {namespace}",
        "  labels:",
    ]
    for key, value in labels.items():
        lines.append(f"    {key}: {value}")

    lines.extend(
        [
            "spec:",
            "  # Keep multiple replicas for basic high availability.",
            f"  replicas: {options['replicas']}",
            "  selector:",
            "    # Selector must match template labels exactly.",
            "    matchLabels:",
            f"      app.kubernetes.io/name: {name}",
            "  template:",
            "    metadata:",
            "      labels:",
        ]
    )
    for key, value in labels.items():
        lines.append(f"        {key}: {value}")

    lines.extend(
        [
            "    spec:",
            "      # Give the application time to shut down cleanly.",
            "      terminationGracePeriodSeconds: 30",
            "      securityContext:",
            "        runAsNonRoot: true",
            "        seccompProfile:",
            "          type: RuntimeDefault",
            "      containers:",
            f"      - name: {name}",
            f"        image: {options['image']}",
            "        imagePullPolicy: IfNotPresent",
            "        ports:",
            f"        - containerPort: {options['port']}",
            "          name: http",
            "        env:",
        ]
    )
    for line in _env_lines(options["env"]).splitlines():
        lines.append(f"        {line}")
    if config_map_name:
        lines.extend(
            [
                "        # Pull app configuration from the generated ConfigMap.",
                "        envFrom:",
                "        - configMapRef:",
                f"            name: {config_map_name}",
            ]
        )
    lines.extend(
        [
            "        resources:",
            "          requests:",
            f"            cpu: \"{options['cpu_request']}\"",
            f"            memory: \"{options['memory_request']}\"",
            "          limits:",
            f"            cpu: \"{options['cpu_limit']}\"",
            f"            memory: \"{options['memory_limit']}\"",
            "        # Readiness controls when the Service can send traffic.",
            "        readinessProbe:",
            "          httpGet:",
            "            path: /readyz",
            "            port: http",
            "          initialDelaySeconds: 5",
            "          periodSeconds: 10",
            "        # Liveness restarts the container if it gets stuck.",
            "        livenessProbe:",
            "          httpGet:",
            "            path: /healthz",
            "            port: http",
            "          initialDelaySeconds: 15",
            "          periodSeconds: 20",
            "        securityContext:",
            "          allowPrivilegeEscalation: false",
            "          readOnlyRootFilesystem: true",
            "          capabilities:",
            "            drop:",
            "            - ALL",
        ]
    )
    return "\n".join(lines)


def _service_yaml(name: str, namespace: str, options: dict[str, Any]) -> str:
    return dedent(
        f"""
        # Service gives the workload a stable in-cluster endpoint.
        apiVersion: v1
        kind: Service
        metadata:
          name: {name}
          namespace: {namespace}
        spec:
          type: ClusterIP
          selector:
            app.kubernetes.io/name: {name}
          ports:
          - name: http
            port: {options["service_port"]}
            targetPort: {options["port"]}
        """
    ).strip()


def _ingress_yaml(name: str, namespace: str, options: dict[str, Any]) -> str:
    return dedent(
        f"""
        # Ingress exposes HTTP traffic to the Service.
        apiVersion: networking.k8s.io/v1
        kind: Ingress
        metadata:
          name: {name}
          namespace: {namespace}
          annotations:
            kubernetes.io/ingress.class: nginx
        spec:
          rules:
          - host: {options["host"]}
            http:
              paths:
              - path: {options["path"]}
                pathType: Prefix
                backend:
                  service:
                    name: {name}
                    port:
                      number: {options["service_port"]}
        """
    ).strip()


def _configmap_yaml(name: str, namespace: str, options: dict[str, Any]) -> str:
    lines = [
        "# ConfigMap stores non-secret runtime settings.",
        "apiVersion: v1",
        "kind: ConfigMap",
        "metadata:",
        f"  name: {name}-config",
        f"  namespace: {namespace}",
        "data:",
    ]
    for line in _config_data_lines(options["config_data"]).splitlines():
        lines.append(f"  {line}")
    return "\n".join(lines)


def _secret_yaml(name: str, namespace: str, options: dict[str, Any]) -> str:
    lines = [
        "# Secret stores sensitive values as plain strings for readability.",
        "apiVersion: v1",
        "kind: Secret",
        "metadata:",
        f"  name: {name}-secret",
        f"  namespace: {namespace}",
        "type: Opaque",
        "stringData:",
    ]
    for line in _string_data_lines(options["secret_data"]).splitlines():
        lines.append(f"  {line}")
    return "\n".join(lines)


def _hpa_yaml(name: str, namespace: str, options: dict[str, Any]) -> str:
    return dedent(
        f"""
        # HPA scales the Deployment based on CPU utilization.
        apiVersion: autoscaling/v2
        kind: HorizontalPodAutoscaler
        metadata:
          name: {name}
          namespace: {namespace}
        spec:
          scaleTargetRef:
            apiVersion: apps/v1
            kind: Deployment
            name: {name}
          minReplicas: {options["min_replicas"]}
          maxReplicas: {options["max_replicas"]}
          metrics:
          - type: Resource
            resource:
              name: cpu
              target:
                type: Utilization
                averageUtilization: {options["target_cpu_utilization"]}
        """
    ).strip()


def _pvc_yaml(name: str, namespace: str, options: dict[str, Any]) -> str:
    lines = [
        "# PVC requests persistent storage for stateful workloads.",
        "apiVersion: v1",
        "kind: PersistentVolumeClaim",
        "metadata:",
        f"  name: {name}-data",
        f"  namespace: {namespace}",
        "spec:",
        "  accessModes:",
    ]
    for mode in options["access_modes"]:
        lines.append(f"  - {mode}")
    lines.extend(
        [
            f"  storageClassName: {options['storage_class_name']}",
            "  resources:",
            "    requests:",
            f"      storage: {options['storage_size']}",
        ]
    )
    return "\n".join(lines)


def generate_kubernetes_yaml(
    resource_type: str,
    name: str,
    namespace: str = "default",
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate production-ready Kubernetes YAML with inline comments."""

    if not name or not name.strip():
        return {"success": False, "data": {}, "error": "Resource name must be provided."}

    normalized_type = (resource_type or "").strip().lower()
    if normalized_type not in SUPPORTED_RESOURCE_TYPES:
        return {
            "success": False,
            "data": {"supported_resource_types": sorted(SUPPORTED_RESOURCE_TYPES)},
            "error": f"Unsupported resource_type '{resource_type}'.",
        }

    opts = _normalize_options(options)
    config_map_name = f"{name}-config"
    docs_map = {
        "deployment": _deployment_yaml(name, namespace, opts),
        "service": _service_yaml(name, namespace, opts),
        "ingress": _ingress_yaml(name, namespace, opts),
        "configmap": _configmap_yaml(name, namespace, opts),
        "secret": _secret_yaml(name, namespace, opts),
        "hpa": _hpa_yaml(name, namespace, opts),
        "pvc": _pvc_yaml(name, namespace, opts),
    }
    docs_map["bundle"] = "\n---\n".join(
        [
            _configmap_yaml(name, namespace, opts),
            _deployment_yaml(name, namespace, {**opts, "config_map_name": config_map_name}),
            _service_yaml(name, namespace, opts),
            _ingress_yaml(name, namespace, opts),
        ]
    )

    yaml_content = docs_map[normalized_type]
    resource_count = 4 if normalized_type == "bundle" else 1
    data = {
        "resource_type": normalized_type,
        "name": name,
        "namespace": namespace,
        "yaml_content": yaml_content,
        "resource_count": resource_count,
    }
    return {"success": True, "data": data, "error": None, **data}
