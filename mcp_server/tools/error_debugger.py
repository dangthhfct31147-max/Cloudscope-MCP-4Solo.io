"""Kubernetes error pattern matching for CloudScope."""

from __future__ import annotations

import re
from difflib import get_close_matches
from typing import Any


POD_COMMANDS = [
    "kubectl describe pod <pod-name> -n <namespace>",
    "kubectl logs <pod-name> -n <namespace> --previous",
    "kubectl get events --sort-by=.metadata.creationTimestamp -n <namespace>",
]
SCHEDULING_COMMANDS = [
    "kubectl describe pod <pod-name> -n <namespace>",
    "kubectl describe nodes",
    "kubectl get events --sort-by=.metadata.creationTimestamp -n <namespace>",
]
STORAGE_COMMANDS = [
    "kubectl get pvc,pv -n <namespace>",
    "kubectl describe pvc <claim-name> -n <namespace>",
    "kubectl get storageclass",
]
ACCESS_COMMANDS = [
    "kubectl auth can-i <verb> <resource> --as system:serviceaccount:<namespace>:<serviceaccount>",
    "kubectl describe rolebinding,clusterrolebinding -A",
]


def _error(
    pattern: str,
    title: str,
    cause: str,
    steps: list[str],
    commands: list[str],
    prevention: str,
) -> dict[str, Any]:
    return {
        "pattern": pattern,
        "title": title,
        "cause": cause,
        "solution_steps": steps,
        "kubectl_commands": commands,
        "prevention": prevention,
    }


ERRORS = [
    _error(r"ImagePullBackOff|ErrImagePull", "ImagePullBackOff", "Kubernetes cannot pull the requested image.", ["Check image name and tag.", "Verify registry credentials or imagePullSecret.", "Test the image pull manually outside the cluster."], POD_COMMANDS, "Pin real image tags and validate registry access before deployment."),
    _error(r"ErrImageNeverPull", "ErrImageNeverPull", "The container is set to Never pull, but the image is not present on the node.", ["Check imagePullPolicy.", "Confirm the image exists locally on the node.", "Change the policy or pre-load the image."], POD_COMMANDS, "Use IfNotPresent unless you fully control node-local images."),
    _error(r"CrashLoopBackOff", "CrashLoopBackOff", "The container starts and exits repeatedly.", ["Inspect previous container logs.", "Check command, env vars, mounted files, and downstream dependencies.", "Fix the root cause before scaling replicas back up."], POD_COMMANDS, "Add health checks, validate config early, and keep startup paths simple."),
    _error(r"exec format error", "CrashLoopBackOff - exec format error", "The image architecture does not match the node CPU architecture.", ["Check node architecture with kubectl get nodes -o wide.", "Build or pull the correct amd64 or arm64 image.", "Publish a multi-arch manifest if needed."], POD_COMMANDS, "Build multi-arch images when clusters are heterogeneous."),
    _error(r"permission denied", "CrashLoopBackOff - permission denied", "The process cannot execute a file or access a required path.", ["Verify file mode and ownership in the image.", "Check runAsNonRoot and readOnlyRootFilesystem settings.", "Confirm mounted volumes expose the expected permissions."], POD_COMMANDS, "Test the container with the same securityContext before shipping."),
    _error(r"no such file or directory", "CrashLoopBackOff - missing entrypoint or file", "The container command points at a missing binary, script, or config file.", ["Inspect the image filesystem.", "Check the entrypoint and command fields.", "Confirm ConfigMaps and Secrets mount to the expected path."], POD_COMMANDS, "Prefer explicit entrypoints and validate file paths in CI."),
    _error(r"panic:|Traceback", "CrashLoopBackOff - app startup failure", "The application crashes during startup due to a code or config error.", ["Read the startup stack trace.", "Compare the runtime env with local dev settings.", "Roll back to the last known good version if needed."], POD_COMMANDS, "Add smoke tests and startup validation before release."),
    _error(r"address already in use|bind: address already in use", "CrashLoopBackOff - port conflict", "The process is trying to bind a port that is already occupied inside the container.", ["Check the application listen port.", "Confirm sidecars or helper processes do not use the same port.", "Align containerPort, app config, and readiness probe settings."], POD_COMMANDS, "Keep a single source of truth for listen ports."),
    _error(r"failed to load config|invalid configuration|parse error", "CrashLoopBackOff - invalid configuration", "The application bootstraps with invalid configuration values or syntax.", ["Validate the mounted config file.", "Confirm environment variables are present.", "Start the app locally with the same config to reproduce."], POD_COMMANDS, "Validate config in CI and use schema checks when possible."),
    _error(r"connection refused", "Connection Refused", "The target service is reachable at the network layer but nothing is listening on the target port.", ["Confirm the destination process is up.", "Check Service selectors and Endpoint population.", "Verify the target port and network policy."], POD_COMMANDS, "Add readiness probes and test service-to-service calls in staging."),
    _error(r"no such host|server misbehaving", "DNS Resolution Failure", "The workload cannot resolve a hostname through cluster DNS.", ["Check the hostname spelling.", "Inspect CoreDNS health.", "Verify the Service name, namespace, and search domain."], POD_COMMANDS, "Use fully qualified service names for critical dependencies."),
    _error(r"i/o timeout|timed out|TLS handshake timeout", "Network Timeout", "The request is hanging due to network path, DNS, or remote service slowness.", ["Check whether the target is reachable from inside the Pod.", "Inspect network policy or firewall rules.", "Measure latency and retry with a shorter path if possible."], POD_COMMANDS, "Set sane timeouts and monitor dependency latency."),
    _error(r"context deadline exceeded", "Context Deadline Exceeded", "The client gave up before the server completed the operation.", ["Find the slow dependency.", "Inspect CPU throttling, storage latency, and network path.", "Raise the timeout only after understanding the bottleneck."], POD_COMMANDS, "Budget realistic timeouts and watch saturation metrics."),
    _error(r"OOMKilled", "OOMKilled", "The container exceeded its memory limit and the kernel terminated it.", ["Check memory usage and limit values.", "Inspect heap growth or unbounded buffering.", "Raise limits only after confirming expected memory needs."], POD_COMMANDS, "Profile memory and set realistic requests and limits."),
    _error(r"Evicted", "Evicted", "The node removed the Pod because of resource pressure.", ["Check node memory, disk, or PID pressure.", "Move the workload to healthier nodes or scale the cluster.", "Review requests so the scheduler can place the Pod more safely."], SCHEDULING_COMMANDS, "Right-size requests and watch node pressure proactively."),
    _error(r"Pending.*Insufficient cpu|0/\d+ nodes are available:.*Insufficient cpu", "Pending - insufficient CPU", "The scheduler cannot find a node with enough free CPU for the Pod request.", ["Check CPU requests on the Pod.", "Scale the node pool or reduce the requested CPU.", "Look for idle workloads consuming reserved CPU."], SCHEDULING_COMMANDS, "Set CPU requests from real measurements instead of guesses."),
    _error(r"Pending.*Insufficient memory|0/\d+ nodes are available:.*Insufficient memory", "Pending - insufficient memory", "The scheduler cannot find a node with enough free memory for the Pod request.", ["Check memory requests on the Pod.", "Scale the node pool or reduce the requested memory.", "Look for memory-heavy neighbors causing fragmentation."], SCHEDULING_COMMANDS, "Keep memory requests realistic and monitor utilization trends."),
    _error(r"didn't match Pod's node affinity|didn't match node selector|node\(s\) didn't match", "Pending - node selector or affinity mismatch", "The Pod requests nodes that do not have the required labels or affinity matches.", ["Inspect node labels.", "Check nodeSelector and affinity rules in the Pod spec.", "Relax overly strict placement rules if they are no longer needed."], SCHEDULING_COMMANDS, "Document node labels and keep placement rules minimal."),
    _error(r"had taint|untolerated taint", "Pending - missing toleration", "The target nodes are tainted and the Pod does not tolerate them.", ["Inspect node taints.", "Add the matching toleration if placement is intentional.", "Use node selectors or affinity together with tolerations for clarity."], SCHEDULING_COMMANDS, "Treat taints as policy and codify matching tolerations deliberately."),
    _error(r"hostport|didn't have free ports for the requested pod ports", "Pending - hostPort conflict", "Another Pod on the node is already using the requested host port.", ["Avoid hostPort unless absolutely necessary.", "Move to a Service or Ingress pattern if possible.", "Schedule onto a different node if the port must be fixed."], SCHEDULING_COMMANDS, "Reserve hostPort for special cases such as node-local agents."),
    _error(r"0/\d+ nodes are available", "FailedScheduling", "The scheduler evaluated nodes and none matched the Pod requirements.", ["Read the full scheduling event details.", "Check requests, selectors, taints, and topology constraints together.", "Remove the tightest constraint first and retry."], SCHEDULING_COMMANDS, "Keep scheduling constraints explicit and tested in non-prod."),
    _error(r"pod has unbound immediate PersistentVolumeClaims|PVC.*not bound|persistentvolumeclaim .* Pending", "PVC Not Bound", "The workload needs storage, but the claim has not been bound to a volume.", ["Describe the PVC and PV objects.", "Check storage class, capacity, and access mode compatibility.", "Confirm the storage provisioner is healthy."], STORAGE_COMMANDS, "Test storage classes with a tiny sample claim before shipping."),
    _error(r"FailedMount", "FailedMount", "A required volume could not be mounted into the Pod.", ["Describe the Pod for mount details.", "Check that the Secret, ConfigMap, or volume exists.", "Confirm the node can reach the storage backend."], STORAGE_COMMANDS, "Prefer small, explicit mounts and validate volume names in CI."),
    _error(r"Multi-Attach error", "Multi-Attach Error", "The same volume cannot be attached to more nodes with the current access mode.", ["Check which nodes currently use the volume.", "Use ReadWriteMany storage if shared access is required.", "Ensure old Pods are fully terminated before rescheduling."], STORAGE_COMMANDS, "Match storage access modes to the workload pattern."),
    _error(r"CreateContainerConfigError", "CreateContainerConfigError", "Kubernetes cannot construct the container spec because referenced config is missing or invalid.", ["Check referenced Secrets and ConfigMaps.", "Inspect environment and volume mounts for typo errors.", "Validate the Pod spec fields against the actual cluster objects."], POD_COMMANDS, "Template object names from one source to avoid drift."),
    _error(r"CreateContainerError", "CreateContainerError", "The runtime failed while creating the container.", ["Inspect kubelet events and runtime logs.", "Check command, mounts, and securityContext.", "Verify the image contains the expected entrypoint and binaries."], POD_COMMANDS, "Keep container startup simple and reproducible."),
    _error(r"RunContainerError", "RunContainerError", "The runtime failed to start the container process.", ["Inspect previous runtime messages.", "Check permissions, entrypoint, and architecture.", "Re-run the image locally with the same command."], POD_COMMANDS, "Use smoke tests that mimic production startup."),
    _error(r"ContainerCreating", "ContainerCreating Stuck", "The Pod is still waiting on image pull, mounts, CNI, or sandbox setup.", ["Describe the Pod to see the latest waiting reason.", "Check image pulls, volume mounts, and node readiness.", "Inspect CNI and kubelet health on the node."], POD_COMMANDS, "Alert on long ContainerCreating times to catch node issues early."),
    _error(r"FailedCreatePodSandBox|Failed to create pod sandbox", "Pod Sandbox Creation Failure", "The node runtime or CNI failed to prepare the Pod sandbox.", ["Check kubelet and CNI logs on the node.", "Confirm the node has enough IPs and network resources.", "Restart node agents only after identifying the failing component."], SCHEDULING_COMMANDS, "Monitor CNI health and IP exhaustion."),
    _error(r"Secret .* not found|secret \".*\" not found", "Secret Not Found", "The Pod references a Secret that does not exist in the namespace.", ["Check the Secret name and namespace.", "Confirm the Secret was applied before the workload.", "Fix any Helm or templating mismatch."], POD_COMMANDS, "Create config dependencies before workloads and keep names centralized."),
    _error(r"ConfigMap .* not found|configmap \".*\" not found", "ConfigMap Not Found", "The Pod references a ConfigMap that does not exist in the namespace.", ["Check the ConfigMap name and namespace.", "Confirm the ConfigMap was applied successfully.", "Fix any templating or rollout ordering issue."], POD_COMMANDS, "Apply config objects ahead of dependent workloads."),
    _error(r"forbidden|is forbidden", "RBAC Forbidden", "The caller identity does not have the required Kubernetes API permission.", ["Identify the failing user or ServiceAccount.", "Check Roles, ClusterRoles, and bindings.", "Grant the narrowest permission that solves the failure."], ACCESS_COMMANDS, "Review RBAC with least privilege instead of using cluster-admin as a shortcut."),
    _error(r"x509: certificate signed by unknown authority|unknown authority", "TLS Trust Failure", "The client does not trust the server certificate chain.", ["Verify the certificate issuer and CA bundle.", "Mount the correct CA into the workload.", "Confirm the hostname matches the certificate SAN."], POD_COMMANDS, "Treat CA distribution as part of environment setup, not ad hoc config."),
    _error(r"Liveness probe failed", "Liveness Probe Failed", "Kubernetes restarted the container because the liveness probe kept failing.", ["Confirm the health endpoint really reflects deadlock or fatal state.", "Increase initialDelaySeconds if the app starts slowly.", "Check CPU throttling or dependency timeouts that make the probe fail."], POD_COMMANDS, "Design liveness probes to detect stuck processes, not slow dependencies."),
    _error(r"Readiness probe failed", "Readiness Probe Failed", "The Pod stays out of service because it fails readiness checks.", ["Check the readiness endpoint behavior.", "Confirm the app is listening on the expected port.", "Make sure downstream dependencies are optional or handled gracefully."], POD_COMMANDS, "Keep readiness strict enough for safety but not dependent on every external system."),
    _error(r"Back-off restarting failed container", "Container Restart Backoff", "Kubernetes is slowing restart attempts because the container keeps crashing.", ["Investigate the original crash reason in logs.", "Do not just delete the Pod repeatedly.", "Roll back or patch the config before retrying."], POD_COMMANDS, "Capture crash diagnostics before automatic restarts hide the root cause."),
    _error(r"exceeded quota|forbidden: exceeded quota", "Quota Exceeded", "The Namespace resource quota blocks the new Pod or object.", ["Describe the ResourceQuota.", "Reduce requests or remove unused objects.", "Ask for a quota increase only if the workload is justified."], ["kubectl describe resourcequota -n <namespace>", "kubectl get pods -n <namespace>"], "Use quota dashboards so teams see pressure before deploy time."),
    _error(r"must be less than or equal to cpu limit|must be less than or equal to memory limit", "LimitRange Validation Error", "The Pod resource settings violate namespace defaults or maximums.", ["Describe the namespace LimitRange.", "Align requests and limits with policy.", "Fix Helm values or manifests generating invalid resources."], ["kubectl describe limitrange -n <namespace>", "kubectl get pod <pod-name> -o yaml -n <namespace>"], "Codify namespace resource policy in templates and examples."),
    _error(r"violates PodSecurity|podsecurity", "PodSecurity Violation", "The Pod spec breaks the enforced Pod Security admission policy.", ["Read the denied field names carefully.", "Drop privileged fields or capabilities.", "Use a compliant securityContext and volume type set."], POD_COMMANDS, "Adopt restricted-compliant defaults in base manifests."),
    _error(r"admission webhook .* denied", "Admission Webhook Denied", "A policy webhook rejected the object during admission.", ["Read the webhook message for the exact policy.", "Check Gatekeeper, Kyverno, or custom admission rules.", "Patch the manifest rather than retrying blindly."], POD_COMMANDS, "Keep policy checks in CI so denials appear before deployment."),
    _error(r"progress deadline exceeded", "Deployment Progress Deadline Exceeded", "The Deployment could not roll out successfully in time.", ["Inspect ReplicaSet and Pod events.", "Check readiness probe failures and image issues.", "Pause rollout or roll back if the new version is unhealthy."], ["kubectl rollout status deployment/<name> -n <namespace>", "kubectl describe deployment <name> -n <namespace>"], "Use canary or staged rollouts for risky changes."),
    _error(r"FailedCreate|ReplicaFailure", "Replica Creation Failure", "The Deployment or ReplicaSet could not create Pods.", ["Check the event stream for quota, policy, or scheduling errors.", "Inspect the child ReplicaSet.", "Resolve the first blocking error before retrying."], ["kubectl describe rs <replicaset> -n <namespace>", "kubectl get events --sort-by=.metadata.creationTimestamp -n <namespace>"], "Watch replica creation events during every rollout."),
    _error(r"NodeNotReady|node is not ready", "Node Not Ready", "The target node is unhealthy or disconnected from the control plane.", ["Check node conditions.", "Inspect kubelet, runtime, and network health.", "Drain and repair or replace the node if instability persists."], ["kubectl describe node <node-name>", "kubectl get nodes"], "Alert on NotReady transitions and automate node remediation."),
    _error(r"backofflimit exceeded|Job has reached the specified backoff limit", "Job Backoff Limit Exceeded", "The Job failed too many times and stopped retrying.", ["Inspect the failed Pod logs.", "Fix the underlying command or data issue.", "Increase backoffLimit only if retries can genuinely help."], ["kubectl describe job <job-name> -n <namespace>", "kubectl logs job/<job-name> -n <namespace>"], "Treat repeated Job failure as a signal, not a retry count problem."),
]

ERROR_TITLES = [entry["title"] for entry in ERRORS]


def debug_kubernetes_error(error_message: str) -> dict[str, Any]:
    """Match a Kubernetes error and return an actionable diagnosis."""

    if not error_message or not error_message.strip():
        return {
            "success": False,
            "data": {"known_errors": ERROR_TITLES[:10]},
            "error": "error_message must be a non-empty string.",
        }

    for entry in ERRORS:
        if re.search(entry["pattern"], error_message, re.IGNORECASE):
            data = {
                "matched": True,
                "error_type": entry["title"],
                "cause": entry["cause"],
                "solution_steps": entry["solution_steps"],
                "kubectl_commands": entry["kubectl_commands"],
                "prevention": entry["prevention"],
            }
            return {"success": True, "data": data, "error": None, **data}

    suggestions = get_close_matches(error_message, ERROR_TITLES, n=3, cutoff=0.15)
    data = {
        "matched": False,
        "error_type": "Unknown Kubernetes Error",
        "cause": "The message did not match CloudScope's known Kubernetes patterns.",
        "solution_steps": [
            "Read the full Pod, Deployment, or Job event stream.",
            "Describe the failing object and inspect previous container logs.",
            "Reduce the problem to the first failing dependency or policy.",
        ],
        "kubectl_commands": POD_COMMANDS,
        "prevention": "Capture the full raw error in logs and alerts so pattern matching is easier next time.",
        "suggestions": suggestions,
    }
    return {"success": True, "data": data, "error": None, **data}
