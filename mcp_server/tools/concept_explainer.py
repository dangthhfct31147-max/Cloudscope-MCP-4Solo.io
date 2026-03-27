"""Concept database and lookup helpers for CloudScope."""

from __future__ import annotations

import re
from difflib import get_close_matches
from typing import Any


def _concept(
    name: str,
    explanation: str,
    analogy: str,
    facts: list[str],
    command: str,
    related: list[str],
    aliases: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "aliases": aliases or [],
        "simple_explanation": explanation,
        "analogy": analogy,
        "key_facts": facts,
        "example_command": command,
        "related_concepts": related,
    }


RAW_CONCEPTS = [
    _concept("Pod", "A Pod is the smallest Kubernetes workload unit.", "A pod is like a lunchbox that keeps one app unit together.", ["Gets one cluster IP.", "Shares localhost across containers.", "Usually managed by a controller."], "kubectl get pods -n default", ["Deployment", "Service", "Node"], aliases=["pods"]),
    _concept("Deployment", "A Deployment manages stateless Pods and rolling updates.", "A Deployment is like a shift manager keeping the right number of workers online.", ["Creates ReplicaSets.", "Supports rollback.", "Handles rolling upgrades."], "kubectl rollout status deployment/my-app", ["Pod", "ReplicaSet", "Service"]),
    _concept("Service", "A Service gives Pods a stable virtual endpoint.", "A Service is like a reception desk that always knows which worker is free.", ["Uses label selectors.", "Keeps a stable DNS name.", "Can be ClusterIP, NodePort, or LoadBalancer."], "kubectl get svc -n default", ["Pod", "Ingress", "NetworkPolicy"]),
    _concept("Ingress", "An Ingress defines HTTP and HTTPS routes into cluster Services.", "Ingress is like a front desk sending visitors to the right room.", ["Routes by host or path.", "Usually terminates TLS.", "Needs an Ingress Controller."], "kubectl get ingress -n default", ["Service", "Ingress Controller", "Service Mesh"]),
    _concept("ConfigMap", "A ConfigMap stores non-secret application settings.", "A ConfigMap is like a settings file mounted next to the app.", ["Can be mounted as files.", "Can become environment variables.", "Should not store credentials."], "kubectl get configmap app-config -o yaml", ["Secret", "Deployment", "Pod"]),
    _concept("Secret", "A Secret stores sensitive values for workloads.", "A Secret is like a locked drawer for tokens and passwords.", ["Can be mounted or injected.", "Works best with least privilege.", "Base64 encoding is not encryption."], "kubectl get secret db-creds -o yaml", ["ConfigMap", "ServiceAccount", "RBAC"]),
    _concept("Namespace", "A Namespace separates teams, apps, or environments in one cluster.", "A Namespace is like a folder that keeps related resources together.", ["Names only need to be unique inside one namespace.", "Works with quotas and RBAC.", "Helps multi-team clusters stay tidy."], "kubectl get ns", ["Cluster", "ResourceQuota", "RoleBinding"]),
    _concept("Node", "A Node is a machine that runs Pods.", "A Node is like a shelf where containers are placed to work.", ["Runs kubelet and a container runtime.", "Can be virtual or bare metal.", "Scheduling decides which pod lands on it."], "kubectl get nodes -o wide", ["Cluster", "Pod", "Control Plane"]),
    _concept("Cluster", "A cluster is the full Kubernetes system of control plane plus nodes.", "A cluster is like the whole factory, not just one machine.", ["Control plane stores desired state.", "Nodes run the workloads.", "Can span multiple machines and zones."], "kubectl cluster-info", ["Control Plane", "Node", "Namespace"]),
    _concept("Persistent Volume", "A Persistent Volume is storage that outlives a single Pod.", "A PV is like a rented locker that stays after one renter leaves.", ["Represents storage capacity.", "Can be provisioned dynamically.", "Bound through a PVC."], "kubectl get pv", ["Persistent Volume Claim", "StatefulSet", "Pod"], aliases=["PV"]),
    _concept("Persistent Volume Claim", "A PVC is an app request for storage.", "A PVC is like a booking form for a locker of a given size.", ["Binds to a PV.", "Lets apps stay storage-vendor neutral.", "Pending PVCs usually mean storage mismatch."], "kubectl get pvc -n default", ["Persistent Volume", "StatefulSet", "StorageClass"], aliases=["PVC"]),
    _concept("StatefulSet", "A StatefulSet manages Pods that need stable identity or storage.", "A StatefulSet is like assigning each database node a fixed desk.", ["Pods keep stable names.", "Often uses volumeClaimTemplates.", "Rollout order is predictable."], "kubectl get statefulset -n default", ["Persistent Volume Claim", "Pod", "Service"]),
    _concept("DaemonSet", "A DaemonSet runs one Pod copy on every selected node.", "A DaemonSet is like installing the same agent on every server rack.", ["Used for logging, storage, and networking.", "New nodes get the pod automatically.", "Common in kube-system."], "kubectl get daemonset -A", ["Node", "Taint", "Toleration"]),
    _concept("Job", "A Job runs Pods until a finite task completes.", "A Job is like hiring a temporary worker for one delivery.", ["Good for batch tasks.", "Can retry on failure.", "Supports parallel completions."], "kubectl get jobs -n default", ["CronJob", "Pod", "BackoffLimit"]),
    _concept("CronJob", "A CronJob creates Jobs on a schedule.", "A CronJob is like a repeating calendar reminder that launches work.", ["Uses cron syntax.", "Creates normal Job objects.", "Keeps run history."], "kubectl get cronjobs -n default", ["Job", "Schedule", "BackoffLimit"]),
    _concept("HorizontalPodAutoscaler", "An HPA scales Pods from metrics like CPU.", "An HPA is like opening more checkout counters when the line grows.", ["Targets Deployments or StatefulSets.", "Needs metrics to work.", "Depends on sensible resource requests."], "kubectl get hpa -n default", ["Deployment", "Metrics Server", "Resource Requests"], aliases=["HPA"]),
    _concept("ResourceQuota", "A ResourceQuota caps total resource use in one Namespace.", "A ResourceQuota is like a spending cap for a team.", ["Can limit CPU, memory, storage, and object counts.", "Protects shared clusters.", "Exceeded quotas reject new workloads."], "kubectl describe resourcequota -n team-a", ["Namespace", "LimitRange", "RBAC"]),
    _concept("LimitRange", "A LimitRange sets default and max resource values in a Namespace.", "A LimitRange is like setting standard room sizes so nobody grabs the whole floor.", ["Can inject default requests.", "Helps teams avoid missing limits.", "Works with ResourceQuota."], "kubectl get limitrange -n default -o yaml", ["ResourceQuota", "Namespace", "HorizontalPodAutoscaler"]),
    _concept("RBAC", "RBAC controls who can do what in Kubernetes.", "RBAC is like badge access for cluster actions.", ["Uses roles plus bindings.", "Least privilege reduces blast radius.", "Forbidden errors often point to RBAC."], "kubectl auth can-i get pods --as system:serviceaccount:default:app", ["Role", "ClusterRole", "ServiceAccount"]),
    _concept("ServiceAccount", "A ServiceAccount is the identity a Pod uses when talking to Kubernetes.", "A ServiceAccount is like the badge handed to a running workload.", ["Pods use a default one unless changed.", "Bindings attach permissions to it.", "Often mapped to cloud IAM identities."], "kubectl get serviceaccount -n default", ["RBAC", "RoleBinding", "Secret"]),
    _concept("Role", "A Role grants permissions within one Namespace.", "A Role is like an office key that works in one branch.", ["Defines verbs on resources.", "Is namespace-scoped.", "Usually paired with a RoleBinding."], "kubectl get role -n default", ["RBAC", "RoleBinding", "Namespace"]),
    _concept("ClusterRole", "A ClusterRole grants cluster-wide or shared permissions.", "A ClusterRole is like a master key for common spaces.", ["Can cover nodes or namespaces.", "Can still be bound inside one namespace.", "Broader than a Role."], "kubectl get clusterrole", ["RBAC", "ClusterRoleBinding", "Role"]),
    _concept("RoleBinding", "A RoleBinding connects a Role or ClusterRole to subjects in one Namespace.", "A RoleBinding is like assigning a specific key to a specific person.", ["Subjects can be users, groups, or ServiceAccounts.", "It is namespace-scoped.", "Common fix for app-level access issues."], "kubectl get rolebinding -n default", ["Role", "ServiceAccount", "RBAC"]),
    _concept("ClusterRoleBinding", "A ClusterRoleBinding grants a ClusterRole across the cluster.", "A ClusterRoleBinding is like company-wide access assigned centrally.", ["Applies beyond one namespace.", "Useful for admins and controllers.", "Should be used carefully."], "kubectl get clusterrolebinding", ["ClusterRole", "RBAC", "ServiceAccount"]),
    _concept("NetworkPolicy", "A NetworkPolicy controls which Pods can talk to each other.", "A NetworkPolicy is like firewall rules between rooms.", ["Supports ingress and egress rules.", "Selects Pods by label.", "Needs a supporting CNI plugin."], "kubectl get networkpolicy -n default", ["Cilium", "Namespace", "Service"]),
    _concept("Helm", "Helm is the package manager for Kubernetes apps.", "Helm is like apt or npm for whole Kubernetes deployments.", ["Packages apps as charts.", "Uses values files for customization.", "Keeps release history for rollback."], "helm list -A", ["Helm Chart", "Helm Release", "GitOps"]),
    _concept("Helm Chart", "A Helm Chart bundles templates, values, and metadata.", "A chart is like a reusable recipe with tunable ingredients.", ["Templates render YAML.", "Charts can depend on other charts.", "Good charts expose useful knobs."], "helm show values bitnami/nginx", ["Helm", "Helm Release", "Deployment"]),
    _concept("Helm Release", "A Helm Release is one deployed instance of a chart.", "A Helm Release is like one baked cake made from the same recipe.", ["The same chart can have many releases.", "Release history enables rollback.", "Release name affects generated resource names."], "helm status my-release -n default", ["Helm", "Helm Chart", "Namespace"]),
    _concept("Docker Image", "A Docker image is an immutable package used to start containers.", "A Docker image is like a sealed blueprint plus parts kit.", ["Built in layers.", "Stored in registries.", "Digests identify exact content."], "docker images", ["Docker Container", "Registry", "Dockerfile"]),
    _concept("Docker Container", "A Docker container is a running instance of an image.", "A container is like turning a blueprint into a working machine.", ["Shares the host kernel.", "Should be disposable.", "Kubernetes runs containers through a runtime."], "docker ps", ["Docker Image", "Container Runtime", "Pod"]),
    _concept("Dockerfile", "A Dockerfile is the recipe used to build an image.", "A Dockerfile is like assembly instructions for packaging an app.", ["Instruction order affects cache hits.", "Multi-stage builds keep runtime images small.", "Base image choice affects security and size."], "docker build -t my-app:latest .", ["Docker Image", "Registry", "Docker Container"]),
    _concept("Docker Compose", "Docker Compose defines multi-container apps on one Docker host.", "Compose is like a local stage manager coordinating several actors.", ["Popular in local development.", "Defines services, networks, and volumes.", "Not a replacement for Kubernetes at scale."], "docker compose up -d", ["Docker Container", "Service", "Helm"]),
    _concept("Registry", "A registry stores and serves container images.", "A registry is like the warehouse where built app packages are stocked.", ["Can be public or private.", "Private registries often need credentials.", "Clusters pull images from registries."], "docker login ghcr.io", ["Docker Image", "Secret", "Pod"]),
    _concept("kubeconfig", "A kubeconfig file stores cluster connections, users, and contexts.", "A kubeconfig is like a contacts book for clusters and credentials.", ["One file can hold many clusters.", "Current context decides where kubectl points.", "Bad kubeconfig often causes auth or connection errors."], "kubectl config view --minify", ["Context", "Cluster", "Namespace"]),
    _concept("Context", "A context is the selected cluster, user, and namespace tuple.", "A context is like choosing which office and account you are working in.", ["kubectl reads the current context.", "Contexts reduce command repetition.", "Checking context avoids production mistakes."], "kubectl config current-context", ["kubeconfig", "Cluster", "Namespace"]),
    _concept("Init Container", "An init container runs before the main app containers.", "An init container is like the setup crew preparing the stage.", ["Runs to completion in sequence.", "Good for migrations and dependency checks.", "If it fails, the main app never starts."], "kubectl describe pod my-app-123", ["Pod", "Sidecar", "Probe"]),
    _concept("Sidecar", "A sidecar is a helper container running beside the main app in one Pod.", "A sidecar is like an assistant riding in the same vehicle.", ["Shares network and volumes with the app.", "Often used for proxies or log shipping.", "Operates as part of the same workload unit."], "kubectl logs my-app-123 -c proxy", ["Pod", "Service Mesh", "Envoy"]),
    _concept("Probe", "A probe is a health check for container lifecycle decisions.", "A probe is like checking whether a restaurant is open, cooking, or ready for customers.", ["Liveness restarts unhealthy containers.", "Readiness decides if traffic should flow.", "Startup protects slow boots from early restarts."], "kubectl describe pod my-app-123", ["Deployment", "Service", "CrashLoopBackOff"], aliases=["liveness probe", "readiness probe", "startup probe"]),
    _concept("Custom Resource Definition", "A CRD teaches Kubernetes a new resource type.", "A CRD is like adding a new form type to the cluster office.", ["Extends the Kubernetes API.", "Often paired with Operators.", "Custom resources can be queried with kubectl."], "kubectl get crd", ["Operator", "API Server", "Controller"], aliases=["CRD"]),
    _concept("Operator", "An Operator automates the lifecycle of a complex app on Kubernetes.", "An Operator is like a robot administrator for one system.", ["Often watches custom resources.", "Encodes operational knowledge in code.", "Common for databases and messaging systems."], "kubectl get deployments -n operators", ["Custom Resource Definition", "StatefulSet", "Controller"]),
    _concept("Prometheus", "Prometheus scrapes and stores time-series metrics.", "Prometheus is like a meter reader collecting measurements on a schedule.", ["Uses pull-based scraping.", "PromQL powers queries and alerts.", "Pairs well with Grafana and Alertmanager."], "kubectl port-forward svc/prometheus 9090:9090", ["Alertmanager", "Grafana", "Metrics"]),
    _concept("Alertmanager", "Alertmanager routes, groups, and deduplicates alerts.", "Alertmanager is like the incident dispatcher deciding who gets paged.", ["Receives alerts from Prometheus.", "Supports silences and inhibition.", "Routes to Slack, email, PagerDuty, and more."], "kubectl get secret alertmanager-main -n monitoring", ["Prometheus", "Grafana", "Incident Response"]),
    _concept("Grafana", "Grafana visualizes metrics, logs, and traces in dashboards.", "Grafana is like the control room wall for system health.", ["Connects to many data sources.", "Dashboards make trends easier to spot.", "Can also manage alerting in many setups."], "kubectl port-forward svc/grafana 3000:80", ["Prometheus", "Alertmanager", "Logs"]),
    _concept("Istio", "Istio is a service mesh for traffic management, security, and observability.", "Istio is like a smart traffic system added to every road between services.", ["Often injects Envoy sidecars.", "Handles mTLS, retries, and traffic splits.", "Adds power but also operational complexity."], "kubectl get virtualservices -A", ["Envoy", "Service Mesh", "Sidecar"]),
    _concept("Envoy", "Envoy is a programmable proxy used at the edge or beside services.", "Envoy is like a smart traffic cop next to your app.", ["Handles routing and retries.", "Exports rich telemetry.", "Common data plane for service meshes."], "kubectl logs deploy/istiod -n istio-system", ["Istio", "Sidecar", "Ingress"]),
    _concept("Cilium", "Cilium provides cloud-native networking and security with eBPF.", "Cilium is like upgrading static road signs into a smart packet traffic system.", ["Can enforce NetworkPolicy.", "Provides deep flow visibility.", "Uses eBPF for performance and control."], "cilium status", ["NetworkPolicy", "Service Mesh", "Node"]),
    _concept("ArgoCD", "ArgoCD continuously syncs cluster state from Git.", "ArgoCD is like an autopilot keeping the cluster aligned with Git.", ["Shows drift between desired and live state.", "Can auto-sync or wait for approval.", "Great for app-centric GitOps workflows."], "argocd app list", ["GitOps", "Flux", "Helm"]),
    _concept("Flux", "Flux is a GitOps toolkit built from composable controllers.", "Flux is like a quiet maintenance crew that keeps config aligned with Git.", ["Fits Kubernetes-native workflows.", "Works well with Helm and Kustomize.", "Common choice for platform teams."], "flux get all -A", ["GitOps", "ArgoCD", "Helm"]),
    _concept("Tekton", "Tekton is a Kubernetes-native CI/CD framework.", "Tekton is like a factory line built from reusable automation blocks.", ["Pipelines are Kubernetes resources.", "Tasks are composable.", "Useful when CI/CD should run inside the cluster."], "kubectl get pipelineruns -A", ["GitOps", "Job", "ArgoCD"]),
    _concept("GitOps", "GitOps treats Git as the source of truth for operations.", "GitOps is like running a system from an approved blueprint archive.", ["Changes flow through pull requests.", "Controllers reconcile live state toward Git.", "Reduces configuration drift."], "git log --oneline", ["ArgoCD", "Flux", "Helm"]),
    _concept("Model Context Protocol", "MCP is an open protocol for exposing tools and resources to AI clients.", "MCP is like a universal power strip for AI tools.", ["Standardizes tool discovery.", "Works for local and remote servers.", "Clear schemas improve agent reliability."], "python mcp_server/server.py --transport stdio", ["AI Agent", "kagent", "agentgateway"], aliases=["MCP"]),
    _concept("AI Agent", "An AI agent combines a model with tools, memory, and control logic to finish tasks.", "An AI agent is like an intern that can reason and use approved tools.", ["Tool quality strongly affects output quality.", "Prompting and guardrails matter.", "Agents amplify both good and bad assumptions."], "python -c \"print('agent ready')\"", ["Model Context Protocol", "kagent", "agentgateway"]),
    _concept("kagent", "kagent is a Kubernetes-focused agent platform that can connect MCP tools to workflows.", "kagent is like an operations workbench for cloud-native agents.", ["Agents can be declared in YAML.", "Useful for cluster-aware assistants.", "CloudScope integrates through an MCP server definition."], "kubectl apply -f kagent/agent.yaml", ["AI Agent", "Model Context Protocol", "agentgateway"]),
    _concept("agentgateway", "agentgateway is a policy and traffic layer for agent or MCP interactions.", "agentgateway is like a guarded checkpoint in front of powerful tools.", ["Can enforce auth and rate limits.", "Improves auditability of tool calls.", "Useful when exposing MCP over HTTP."], "kubectl apply -f agentgateway/gateway-config.yaml", ["Model Context Protocol", "kagent", "agentregistry"]),
    _concept("agentregistry", "agentregistry is a catalog for publishing and discovering reusable agents.", "agentregistry is like an app store shelf for agents.", ["Good entries need clear docs.", "Improves reuse and discoverability.", "Judges care about install clarity."], "cat README.md", ["kagent", "agentgateway", "Model Context Protocol"]),
    _concept("Service Mesh", "A service mesh adds a dedicated communication layer between services.", "A service mesh is like installing traffic lights and cameras on every service road.", ["Usually adds mTLS and traffic policy.", "Often relies on sidecars or ambient data plane.", "Comes with extra operational overhead."], "kubectl get peerauthentication -A", ["Istio", "Envoy", "Sidecar"]),
    _concept("Container Runtime", "A container runtime pulls images and runs containers on a host.", "A runtime is like the engine that turns a package into a running machine.", ["Common runtimes are containerd and CRI-O.", "Kubernetes talks to it through CRI.", "Runtime issues can break sandbox startup."], "crictl ps", ["Docker Container", "Pod", "Node"]),
    _concept("Control Plane", "The control plane stores cluster state and coordinates work.", "The control plane is like headquarters for the cluster.", ["Includes the API server, scheduler, and controllers.", "If it is unhealthy, cluster management breaks fast.", "etcd is the backing state store."], "kubectl get componentstatuses", ["Cluster", "Node", "etcd"]),
    _concept("ReplicaSet", "A ReplicaSet ensures a target number of identical Pods are running.", "A ReplicaSet is like keeping an exact number of bulbs lit in a sign.", ["Deployments usually manage ReplicaSets for you.", "Uses label selectors.", "Direct management is uncommon for app teams."], "kubectl get rs -n default", ["Deployment", "Pod", "Selector"]),
    _concept("Ingress Controller", "An Ingress Controller watches Ingress objects and configures real traffic routing.", "An Ingress Controller is like the crew that reads the routing plan and opens the right doors.", ["Without one, an Ingress object does nothing.", "Controllers often support custom annotations.", "Examples include NGINX, Traefik, and Envoy-based controllers."], "kubectl get pods -n ingress-nginx", ["Ingress", "Service", "Envoy"]),
]


def normalize_term(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _tokenize(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.lower()))


CONCEPTS: dict[str, dict[str, Any]] = {}
ALIAS_TO_CONCEPT: dict[str, str] = {}
DISPLAY_NAMES: list[str] = []

for item in RAW_CONCEPTS:
    key = normalize_term(item["name"])
    aliases = sorted({item["name"], *item["aliases"]})
    CONCEPTS[key] = {
        "name": item["name"],
        "simple_explanation": item["simple_explanation"],
        "analogy": item["analogy"],
        "key_facts": item["key_facts"],
        "example_command": item["example_command"],
        "related_concepts": item["related_concepts"],
    }
    for alias in aliases:
        ALIAS_TO_CONCEPT[normalize_term(alias)] = key
    DISPLAY_NAMES.append(item["name"])


def list_supported_concepts() -> list[str]:
    """Return all supported concept names."""

    return sorted(DISPLAY_NAMES)


def resolve_concept_key(concept: str) -> str | None:
    """Resolve a user term to a concept key."""

    return ALIAS_TO_CONCEPT.get(normalize_term(concept))


def find_relevant_concepts(query: str, limit: int = 5) -> list[dict[str, str]]:
    """Return lightweight concept hits for docs fallback."""

    normalized_query = normalize_term(query)
    query_tokens = _tokenize(query)
    ranked: list[tuple[int, dict[str, str]]] = []

    for item in RAW_CONCEPTS:
        key = normalize_term(item["name"])
        aliases = {normalize_term(alias) for alias in item["aliases"]}
        aliases.add(key)
        searchable = " ".join(
            [
                item["name"],
                item["simple_explanation"],
                " ".join(item["key_facts"]),
                " ".join(item["related_concepts"]),
                " ".join(item["aliases"]),
            ]
        ).lower()

        score = 0
        if normalized_query in aliases:
            score += 100
        if normalized_query and normalized_query in key:
            score += 35
        if query_tokens:
            score += len(query_tokens & _tokenize(item["name"])) * 18
            score += len(query_tokens & _tokenize(searchable)) * 4

        if score > 0:
            ranked.append(
                (
                    score,
                    {
                        "title": item["name"],
                        "summary": item["simple_explanation"],
                        "source_url": f"https://cloudscope.local/concepts/{key}",
                    },
                )
            )

    ranked.sort(key=lambda entry: (-entry[0], entry[1]["title"]))
    return [payload for _, payload in ranked[:limit]]


def explain_concept(concept: str) -> dict[str, Any]:
    """Explain a concept or return the closest three suggestions."""

    if not concept or not concept.strip():
        return {
            "success": False,
            "data": {"suggestions": list_supported_concepts()[:3]},
            "error": "Concept must be a non-empty string.",
        }

    concept_key = resolve_concept_key(concept)
    if concept_key:
        data = {"concept": CONCEPTS[concept_key]["name"], **CONCEPTS[concept_key]}
        return {"success": True, "data": data, "error": None, **data}

    suggestions = [item["title"] for item in find_relevant_concepts(concept, limit=3)]
    if not suggestions:
        suggestions = get_close_matches(concept, list_supported_concepts(), n=3, cutoff=0.35)

    return {
        "success": False,
        "data": {"suggestions": suggestions},
        "error": f"Concept '{concept}' was not found in the CloudScope knowledge base.",
        "suggestions": suggestions,
    }
