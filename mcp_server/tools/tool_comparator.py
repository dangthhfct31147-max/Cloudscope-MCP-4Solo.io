"""Cloud-native tool comparison database for CloudScope."""

from __future__ import annotations

from difflib import get_close_matches
from typing import Any


def _comparison(
    tool_a: str,
    tool_b: str,
    summary: str,
    dimensions: dict[str, dict[str, str]],
    use_a: list[str],
    use_b: list[str],
    verdict: str,
) -> dict[str, Any]:
    return {
        "tool_a": tool_a,
        "tool_b": tool_b,
        "summary": summary,
        "dimensions": dimensions,
        "use_cases": {
            f"use_{tool_a.replace(' ', '_')}_when": use_a,
            f"use_{tool_b.replace(' ', '_')}_when": use_b,
        },
        "verdict": verdict,
    }


def _dims(
    ease: tuple[str, str],
    performance: tuple[str, str],
    community: tuple[str, str],
    fit: tuple[str, str],
    learning: tuple[str, str],
) -> dict[str, dict[str, str]]:
    return {
        "ease_of_use": {"winner": ease[0], "reasoning": ease[1]},
        "performance": {"winner": performance[0], "reasoning": performance[1]},
        "community": {"winner": community[0], "reasoning": community[1]},
        "cloud_native_fit": {"winner": fit[0], "reasoning": fit[1]},
        "learning_curve": {"winner": learning[0], "reasoning": learning[1]},
    }


RAW_COMPARISONS = [
    _comparison("docker", "podman", "Both run OCI containers, but Podman is daemonless and rootless by default.", _dims(("docker", "More tutorials and familiar workflows."), ("podman", "No long-running daemon overhead."), ("docker", "Much larger ecosystem and mindshare."), ("podman", "Cleaner fit for rootless Linux hosts."), ("docker", "New users find the tooling more widely documented.")), ["Your team already uses Docker Desktop.", "You need the largest tutorial ecosystem."], ["You want rootless containers by default.", "You run heavily on Fedora or RHEL."], "Choose Podman for security-first Linux environments. Choose Docker when broad familiarity matters more."),
    _comparison("docker", "containerd", "Docker is a developer platform while containerd is a lower-level runtime.", _dims(("docker", "Comes with build, run, and registry workflows in one tool."), ("containerd", "Less overhead because it focuses on runtime concerns."), ("docker", "Developer ecosystem is much larger."), ("containerd", "It sits directly in many Kubernetes stacks."), ("docker", "The workflow is easier for app teams.")), ["Developers need fast local builds and runs.", "You want one CLI for day-to-day container work."], ["You are building a platform or runtime layer.", "You need a slim runtime foundation for Kubernetes nodes."], "Use Docker for developer experience. Use containerd for infrastructure plumbing."),
    _comparison("helm", "kustomize", "Helm packages apps as parameterized charts, while Kustomize patches plain YAML.", _dims(("kustomize", "No templating language to learn."), ("helm", "Templating reduces duplication in large app bundles."), ("helm", "More packaged applications are published as charts."), ("kustomize", "Native fit for GitOps overlays and raw manifests."), ("kustomize", "Patch-based workflows are simpler to start with.")), ["You publish reusable app packages.", "You need release history and rollback support."], ["You prefer plain YAML plus overlays.", "You want fewer templating abstractions in Git."], "Helm wins for reusable distribution. Kustomize wins for transparent environment overlays."),
    _comparison("argocd", "flux", "Both are GitOps controllers, but ArgoCD is more app-centric while Flux is more controller-centric.", _dims(("argocd", "UI and workflows are easier for many teams."), ("flux", "Controller model stays lighter in many clusters."), ("argocd", "Wider day-2 mindshare in app delivery."), ("flux", "Feels closer to native Kubernetes reconciliation."), ("argocd", "The UI shortens the learning ramp.")), ["You want a strong UI and app dashboard.", "Application team self-service is important."], ["You prefer modular controllers and Git-first operations.", "Platform teams want fewer extra layers."], "ArgoCD is easier to demo and operate visually. Flux is excellent for platform-native GitOps."),
    _comparison("istio", "linkerd", "Istio is feature-rich, while Linkerd is intentionally simpler and lighter.", _dims(("linkerd", "Smaller surface area and easier defaults."), ("linkerd", "Lower operational overhead in many clusters."), ("istio", "Bigger ecosystem and enterprise adoption."), ("istio", "Richer traffic policy and security capabilities."), ("linkerd", "Operators get productive faster.")), ["You need advanced traffic shaping, policy, and ecosystem features.", "Multi-team platform control is a priority."], ["You want core mesh features with less complexity.", "Teams are sensitive to operational burden."], "Pick Istio for maximum control. Pick Linkerd for a leaner service mesh."),
    _comparison("prometheus", "datadog", "Prometheus is open-source and self-managed, while Datadog is a managed observability platform.", _dims(("datadog", "Managed UX and integrations are smoother out of the box."), ("prometheus", "Pull-based scraping is efficient for Kubernetes metrics."), ("prometheus", "Open-source community is huge."), ("prometheus", "Cloud-native metrics workflows are a natural fit."), ("datadog", "Less infrastructure to learn and maintain.")), ["You want open-source metrics and own the stack.", "PromQL and Kubernetes-native monitoring are key."], ["You want one managed platform across metrics, logs, and traces.", "You prefer paying for speed over operating the stack."], "Prometheus fits platform engineering. Datadog fits teams that value managed convenience."),
    _comparison("grafana", "kibana", "Grafana excels at multi-source observability dashboards, while Kibana shines with Elasticsearch-native log exploration.", _dims(("grafana", "Dashboarding is more flexible across many backends."), ("kibana", "Elastic-native search can feel faster for log-heavy use cases."), ("grafana", "Broader observability dashboard adoption."), ("grafana", "Pairs naturally with Prometheus and Loki."), ("grafana", "The mental model is simpler for dashboards.")), ["You need dashboards across metrics, logs, and traces.", "Prometheus or Loki is already in your stack."], ["Elasticsearch is your center of gravity.", "Your main use case is deep log forensics."], "Grafana is the default choice for cloud-native dashboards. Kibana wins in Elastic-centric estates."),
    _comparison("eks", "gke", "EKS and GKE are managed Kubernetes services, but GKE is often more opinionated and EKS is more AWS-native.", _dims(("gke", "Cluster setup and UX are typically smoother."), ("gke", "Autopilot and managed features reduce ops load."), ("eks", "AWS market share keeps EKS extremely common."), ("gke", "Google's Kubernetes heritage shows in the platform ergonomics."), ("gke", "Teams ramp faster with clearer defaults.")), ["Your organization is deeply invested in AWS services.", "You want native IAM and networking alignment with AWS."], ["You want strong managed ergonomics.", "You prefer faster day-1 Kubernetes adoption."], "Pick EKS for AWS gravity. Pick GKE for a polished Kubernetes experience."),
    _comparison("eks", "aks", "EKS is AWS-native and AKS is Azure-native, with different identity and networking strengths.", _dims(("aks", "AKS setup often feels simpler for Microsoft estates."), ("eks", "AWS primitives offer deep tuning and ecosystem breadth."), ("eks", "AWS community scale remains larger."), ("aks", "Fits cleanly with Entra ID and Azure governance."), ("aks", "Microsoft teams usually onboard faster.")), ["You are standardized on AWS networking and IAM.", "You need the AWS ecosystem around the cluster."], ["You are standardized on Azure and Entra ID.", "You want Kubernetes to fit existing Microsoft governance flows."], "Choose the cluster that matches your cloud gravity. Cross-cloud convenience rarely beats native integration."),
    _comparison("kubernetes", "docker swarm", "Kubernetes is a full orchestration platform while Docker Swarm is a lighter orchestration layer.", _dims(("docker swarm", "The model is easier for small teams."), ("kubernetes", "Better scheduling, scaling, and ecosystem depth."), ("kubernetes", "Ecosystem size is not close."), ("kubernetes", "It is the default cloud-native control plane."), ("docker swarm", "Much less to learn initially.")), ["You need the standard platform for production cloud-native systems.", "You need broad ecosystem integrations."], ["You only need simple orchestration for a small footprint.", "You value a minimal control plane over ecosystem depth."], "Kubernetes is the strategic choice. Swarm is only compelling when requirements stay very small."),
    _comparison("kubernetes", "nomad", "Kubernetes dominates container orchestration, while Nomad is a simpler scheduler that spans more workload types.", _dims(("nomad", "Smaller API surface and operating model."), ("nomad", "Lightweight architecture can reduce overhead."), ("kubernetes", "The ecosystem gap is massive."), ("kubernetes", "Best fit for cloud-native container platforms."), ("nomad", "Fewer moving parts to understand.")), ["You need the broadest CNCF ecosystem and managed offerings.", "Your platform is container-first."], ["You want a simpler scheduler for mixed workloads.", "You already use the HashiCorp stack heavily."], "Kubernetes wins for mainstream cloud-native adoption. Nomad wins only when simplicity and multi-workload scheduling dominate."),
    _comparison("tekton", "github actions", "Tekton is Kubernetes-native CI/CD, while GitHub Actions is a hosted workflow platform tied to GitHub.", _dims(("github actions", "Fastest setup for most application teams."), ("tekton", "Runs natively inside Kubernetes and can stay close to the workload."), ("github actions", "Much broader day-to-day usage."), ("tekton", "Better fit when CI/CD belongs inside the cluster."), ("github actions", "YAML workflow onboarding is simpler.")), ["You need cluster-native pipelines and custom platform control.", "Your delivery system must live inside Kubernetes."], ["Your source of truth is GitHub.", "You want fast CI/CD adoption with less platform work."], "Use Tekton for platform-native pipelines. Use GitHub Actions for rapid team adoption."),
    _comparison("tekton", "argo workflows", "Tekton focuses on CI/CD primitives while Argo Workflows excels at general workflow orchestration.", _dims(("tekton", "The CI/CD story is more direct."), ("argo workflows", "Workflow DAG features are stronger for complex orchestration."), ("argo workflows", "Broader workflow mindshare beyond CI/CD."), ("tekton", "Better fit for Kubernetes-native delivery pipelines."), ("tekton", "Easier when your goal is just CI/CD.")), ["You want pipeline building blocks for software delivery.", "Supply-chain oriented CI/CD matters most."], ["You need rich DAGs, fan-out, and data workflow patterns.", "You orchestrate more than software delivery."], "Tekton is the better CI/CD specialist. Argo Workflows is the better general workflow engine."),
    _comparison("helm", "plain manifests", "Helm adds packaging and templating, while plain manifests maximize transparency.", _dims(("plain manifests", "No packaging layer to learn."), ("helm", "Templating cuts repetition at scale."), ("helm", "Chart ecosystem and tooling are mature."), ("plain manifests", "Raw YAML fits GitOps reviews very directly."), ("plain manifests", "What you read is what you apply.")), ["You need reusable app bundles across many environments.", "You want release history and chart distribution."], ["Your manifests are small and stable.", "You want the simplest possible review surface."], "Use plain manifests until repetition hurts. Move to Helm when packaging and reuse become real needs."),
    _comparison("cilium", "calico", "Both secure Kubernetes networking, but Cilium leans into eBPF while Calico remains widely familiar.", _dims(("calico", "Operational patterns are widely known."), ("cilium", "eBPF data plane gives strong visibility and speed."), ("calico", "Longstanding install base is still huge."), ("cilium", "Modern cloud-native networking features are a strong fit."), ("calico", "Teams often learn it faster.")), ["You want a familiar and proven network policy story.", "Your team values predictable operational patterns."], ["You want deep observability, eBPF, and advanced networking features.", "Performance and network visibility are strategic."], "Calico is the safer default for familiarity. Cilium is the forward-looking choice for advanced networking."),
    _comparison("envoy", "nginx ingress", "Envoy is a programmable proxy platform, while NGINX Ingress is a popular ingress-focused controller.", _dims(("nginx ingress", "Ingress use cases are easier to start with."), ("envoy", "More flexible and modern traffic features."), ("nginx ingress", "Very common in clusters and tutorials."), ("envoy", "Better fit when you need programmable traffic control."), ("nginx ingress", "The ingress-specific model is simpler.")), ["You need a battle-tested ingress controller with broad examples.", "Your routing needs are straightforward."], ["You need richer proxy behavior or mesh alignment.", "Programmable traffic policies are important."], "NGINX Ingress is the simple gateway default. Envoy wins when traffic engineering gets serious."),
    _comparison("kagent", "langchain", "kagent is oriented toward Kubernetes agents and integrations, while LangChain is a broader agent and workflow framework.", _dims(("langchain", "More tutorials and general-purpose examples exist."), ("kagent", "Less glue is needed for Kubernetes-centric agent workflows."), ("langchain", "Broader LLM developer community."), ("kagent", "Closer fit for cluster-aware agents and MCP integrations."), ("langchain", "More people have seen the abstractions before.")), ["Your agent lives in or near Kubernetes operations.", "You want MCP and platform integration first."], ["You need a broader application framework for LLM workflows.", "Your scope goes beyond Kubernetes agents."], "Use kagent for cloud-native agent operations. Use LangChain for broader application-level agent systems."),
    _comparison("kagent", "agentgateway", "kagent defines and runs agents, while agentgateway governs and protects traffic to their tools.", _dims(("kagent", "It is the direct agent authoring surface."), ("agentgateway", "Adds policy without changing each tool implementation."), ("kagent", "Agent builders interact with it more often."), ("agentgateway", "A stronger fit for securing exposed agent interfaces."), ("kagent", "The agent concept is easier to grasp than gateway policy.")), ["You are defining agent behavior and tool wiring.", "You need an execution home for the agent."], ["You need auth, rate limits, and audit around agent traffic.", "You expose agent tools over HTTP and need controls."], "These are complementary, not substitutes. kagent runs the agent; agentgateway protects the edges."),
    _comparison("agentgateway", "kong", "Both can sit in front of APIs, but agentgateway is specialized for agent and MCP traffic while Kong is a general API gateway.", _dims(("kong", "General API gateway patterns are more widely familiar."), ("kong", "Broader plugin ecosystem and mature performance tuning."), ("kong", "Larger long-term gateway community."), ("agentgateway", "Closer fit for MCP and agent policy semantics."), ("kong", "Teams with API gateway experience ramp faster.")), ["You need a broad API gateway for many protocols and teams.", "A mature plugin ecosystem matters."], ["You want controls tailored to agent and MCP workloads.", "Tool-call auditing and agent-aware policy is the focus."], "Use Kong for broad API gateway needs. Use agentgateway when the domain is specifically agent traffic."),
    _comparison("mcp", "rest api", "REST APIs expose raw endpoints, while MCP exposes tool semantics in a model-friendly contract.", _dims(("rest api", "HTTP endpoint concepts are universal."), ("rest api", "Lean transport overhead and broad optimization options."), ("rest api", "Ecosystem is vastly larger."), ("mcp", "Tool schemas and discovery fit AI clients better."), ("rest api", "Most teams know REST first.")), ["You need generic machine-to-machine integration.", "Your clients are not primarily AI agents."], ["You need AI clients to discover and call tools safely.", "You want tool descriptions and schema to travel together."], "REST is the general integration baseline. MCP is the better contract for AI tool use."),
    _comparison("docker compose", "helm", "Docker Compose targets local multi-container apps, while Helm targets Kubernetes packaging.", _dims(("docker compose", "Faster for local development."), ("helm", "Scales better to repeated cluster deployments."), ("docker compose", "Many developers meet it early."), ("helm", "Fits Kubernetes release workflows and packaging."), ("docker compose", "Less abstraction for small local stacks.")), ["You are building or demoing locally on one Docker host.", "You want the quickest local startup path."], ["You are deploying to Kubernetes.", "You want reusable app packaging and release management."], "Use Compose locally and Helm in clusters. They solve different stages of the lifecycle."),
    _comparison("vault", "kubernetes secrets", "Vault is a dedicated secrets platform, while Kubernetes Secrets are a native cluster primitive.", _dims(("kubernetes secrets", "Native and easy to start with."), ("vault", "Dynamic secrets and stronger secret lifecycle controls."), ("vault", "Dedicated secrets community and patterns are mature."), ("vault", "Better fit for serious multi-system secret management."), ("kubernetes secrets", "Far less to stand up initially.")), ["You need simple cluster-local secret delivery.", "Your secret requirements are modest."], ["You need rotation, dynamic credentials, or central secret governance.", "Many systems beyond Kubernetes consume the same secrets."], "Kubernetes Secrets are enough for simple cases. Vault wins when secret management becomes a platform concern."),
]


COMPARISONS = {frozenset({item["tool_a"], item["tool_b"]}): item for item in RAW_COMPARISONS}
SUPPORTED_TOOLS = sorted({tool for item in RAW_COMPARISONS for tool in (item["tool_a"], item["tool_b"])})
SUPPORTED_PAIRS = sorted([f'{item["tool_a"]} vs {item["tool_b"]}' for item in RAW_COMPARISONS])


def compare_cloud_tools(tool_a: str, tool_b: str) -> dict[str, Any]:
    """Compare two cloud-native tools across five practical dimensions."""

    left = (tool_a or "").strip().lower()
    right = (tool_b or "").strip().lower()
    if not left or not right:
        return {
            "success": False,
            "data": {"supported_pairs": SUPPORTED_PAIRS[:10]},
            "error": "Both tool_a and tool_b must be provided.",
        }

    comparison = COMPARISONS.get(frozenset({left, right}))
    if comparison:
        data = {
            "summary": comparison["summary"],
            "dimensions": comparison["dimensions"],
            "use_cases": comparison["use_cases"],
            "verdict": comparison["verdict"],
            "compared_tools": [comparison["tool_a"], comparison["tool_b"]],
        }
        return {"success": True, "data": data, "error": None, **data}

    suggestions = get_close_matches(left, SUPPORTED_TOOLS, n=3, cutoff=0.4) + get_close_matches(
        right, SUPPORTED_TOOLS, n=3, cutoff=0.4
    )
    data = {
        "supported_pairs": SUPPORTED_PAIRS,
        "closest_supported_tools": sorted(set(suggestions)),
    }
    return {
        "success": False,
        "data": data,
        "error": f"No comparison is available for '{tool_a}' and '{tool_b}'.",
    }
