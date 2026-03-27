"""CloudScope MCP server entrypoint."""

from __future__ import annotations

import argparse
from typing import Any

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse

try:
    from mcp_server.tools.concept_explainer import explain_concept as explain_concept_tool
    from mcp_server.tools.docs_search import search_docs as search_docs_tool
    from mcp_server.tools.error_debugger import debug_kubernetes_error as debug_kubernetes_error_tool
    from mcp_server.tools.tool_comparator import compare_cloud_tools as compare_cloud_tools_tool
    from mcp_server.tools.yaml_generator import generate_kubernetes_yaml as generate_kubernetes_yaml_tool
except ImportError:  # pragma: no cover - fallback for direct script execution
    from tools.concept_explainer import explain_concept as explain_concept_tool
    from tools.docs_search import search_docs as search_docs_tool
    from tools.error_debugger import debug_kubernetes_error as debug_kubernetes_error_tool
    from tools.tool_comparator import compare_cloud_tools as compare_cloud_tools_tool
    from tools.yaml_generator import generate_kubernetes_yaml as generate_kubernetes_yaml_tool


mcp = FastMCP(
    name="CloudScope",
    instructions="AI-powered cloud-native learning assistant for Kubernetes, Docker, Helm, and agent ecosystems.",
)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(_: Request) -> PlainTextResponse:
    """Simple HTTP health endpoint for probes and gateways."""

    return PlainTextResponse("ok")


@mcp.custom_route("/metrics", methods=["GET"])
async def metrics(_: Request) -> PlainTextResponse:
    """Tiny Prometheus-style metric surface for demos."""

    payload = "\n".join(
        [
            "# HELP cloudscope_info Static build information.",
            "# TYPE cloudscope_info gauge",
            'cloudscope_info{name="CloudScope",version="1.0.0"} 1',
            "# HELP cloudscope_tools_total Number of published MCP tools.",
            "# TYPE cloudscope_tools_total gauge",
            "cloudscope_tools_total 5",
        ]
    )
    return PlainTextResponse(payload)


@mcp.tool
def search_docs(query: str, technology: str = "kubernetes") -> dict[str, Any]:
    """
    Search official documentation for cloud-native technologies.

    Supports: kubernetes, docker, helm, prometheus, grafana, istio, cilium.

    Args:
        query: Search query string.
        technology: Which documentation set to search.

    Returns:
        dict with keys: success, data, results, cached, fallback_used, error.
    """

    return search_docs_tool(query=query, technology=technology)


@mcp.tool
def explain_concept(concept: str) -> dict[str, Any]:
    """
    Explain a cloud-native concept in plain English with an analogy.

    Covers 60+ concepts including Pod, Deployment, Service, Ingress,
    ConfigMap, Secret, StatefulSet, DaemonSet, RBAC, Helm, MCP, kagent,
    agentgateway, and agentregistry.

    Args:
        concept: Cloud-native term to explain.

    Returns:
        dict with keys: success, data, concept, simple_explanation, analogy,
        key_facts, example_command, related_concepts, suggestions, error.
    """

    return explain_concept_tool(concept=concept)


@mcp.tool
def generate_kubernetes_yaml(
    resource_type: str,
    name: str,
    namespace: str = "default",
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Generate production-ready Kubernetes YAML with inline comments.

    Supports: deployment, service, ingress, configmap, secret, hpa,
    pvc, and bundle.

    Args:
        resource_type: One of deployment/service/ingress/configmap/secret/hpa/pvc/bundle.
        name: Resource name.
        namespace: Kubernetes namespace.
        options: Extra options such as image, replicas, port, host, or storage_size.

    Returns:
        dict with keys: success, data, yaml_content, resource_count, error.
    """

    return generate_kubernetes_yaml_tool(
        resource_type=resource_type,
        name=name,
        namespace=namespace,
        options=options,
    )


@mcp.tool
def debug_kubernetes_error(error_message: str) -> dict[str, Any]:
    """
    Diagnose Kubernetes errors and return step-by-step fixes.

    Covers 40+ failure patterns including ImagePullBackOff,
    CrashLoopBackOff, OOMKilled, Evicted, Pending, RBAC forbidden,
    PVC not bound, and probe failures.

    Args:
        error_message: Raw error text from kubectl, events, or logs.

    Returns:
        dict with keys: success, data, matched, error_type, cause,
        solution_steps, kubectl_commands, prevention, error.
    """

    return debug_kubernetes_error_tool(error_message=error_message)


@mcp.tool
def compare_cloud_tools(tool_a: str, tool_b: str) -> dict[str, Any]:
    """
    Compare two cloud-native tools across five practical dimensions.

    Supports 20+ pairs such as docker/podman, helm/kustomize,
    argocd/flux, istio/linkerd, prometheus/datadog, eks/gke,
    kagent/langchain, and mcp/rest api.

    Args:
        tool_a: First tool name.
        tool_b: Second tool name.

    Returns:
        dict with keys: success, data, summary, dimensions, use_cases,
        verdict, compared_tools, error.
    """

    return compare_cloud_tools_tool(tool_a=tool_a, tool_b=tool_b)


app = mcp.http_app()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the CloudScope MCP server.")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="0.0.0.0", help="HTTP bind host.")
    parser.add_argument("--port", type=int, default=8000, help="HTTP bind port.")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    if args.transport == "http":
        mcp.run(transport="http", host=args.host, port=args.port)
    else:
        mcp.run()
