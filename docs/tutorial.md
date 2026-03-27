# Building CloudScope: An MCP Server for Cloud-Native Learning

## Introduction - Why I Built This

I built CloudScope because I kept seeing developers copy cloud-native commands without really understanding them. They could run a Deployment, but not explain why a StatefulSet behaved differently, why a Pod stayed Pending, or when Helm was a better fit than Kustomize. That gap matters even more once AI agents enter the workflow.

My goal was to make an AI agent genuinely useful for cloud-native learning, so I split the product into five concrete tools instead of one vague "Kubernetes helper":

1. Search official docs
2. Explain cloud-native concepts in plain English
3. Generate production-ready Kubernetes YAML
4. Debug common Kubernetes failures
5. Compare cloud-native tools objectively

That split matters because agents behave better when tool boundaries are explicit. Docs search should not guess YAML, and a YAML generator should not pretend to be a debugger. I also wanted the project to feel like a product, so the repo includes a dashboard, kagent integration, gateway policy, and registry-ready docs.

## What is MCP?

MCP, or Model Context Protocol, is a standard way for AI clients to discover and call external tools. I think of it as the contract between a model and the systems around it.

Without MCP, tool use becomes one-off glue code and unreliable prompt conventions. With MCP, the server exposes structured inputs, outputs, and descriptions that the client can inspect. That is why CloudScope is an MCP server instead of a standalone chatbot: the same backend can work in a desktop client, a local workflow, or a Kubernetes-hosted agent.

## Architecture Overview

At a high level, CloudScope looks like this:

```text
Developer / Judge
        |
        v
   AI Agent Client
        |
        v
+-------------------+
|   CloudScope MCP  |
|   FastMCP Server  |
+-------------------+
 |       |       |       |       |
 |       |       |       |       |
 v       v       v       v       v
Docs   Explain   YAML   Debug   Compare
Search Concept Generate Errors  Tools
        |
        v
  kagent + agentgateway + agentregistry
```

The MCP server is the core. `kagent` shows where the agent runs, `agentgateway` shows how I would protect the endpoint, and the dashboard makes the whole flow easy to demo.

## Prerequisites

Before I run CloudScope, I assume I have:

- Python 3.11 or newer
- `pip` or another Python package installer
- A browser to open the dashboard
- Optional: a Kubernetes cluster if I want to try the kagent flow

The local path is intentionally lightweight: stdio for desktop MCP clients, HTTP for gateways or hosted agent platforms.

## Step 1: Install and Run the MCP Server

I start by creating a virtual environment and installing the backend dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r mcp_server/requirements.txt
```

For the fastest local path, I run the server over stdio:

```bash
python mcp_server/server.py
```

If I want to route traffic over HTTP instead, I switch transports:

```bash
python mcp_server/server.py --transport http --host 0.0.0.0 --port 8000
```

I built the server with FastMCP because each tool can stay readable and explicitly described.

## Step 2: Connect to Claude Desktop

For a local desktop client, I use a minimal MCP server entry. In Claude Desktop style JSON, it looks like this:

```json
{
  "mcpServers": {
    "cloudscope": {
      "command": "python",
      "args": ["mcp_server/server.py"]
    }
  }
}
```

I like this setup because it proves the tool design without extra infrastructure.

## Step 3: Deploy with kagent on Kubernetes

Once the local flow works, I can show the stronger cloud-native story: CloudScope behind a Kubernetes-hosted agent.

I apply the manifest:

```bash
kubectl apply -f kagent/agent.yaml
kubectl get agent -n cloudscope
```

The key part of the manifest is the MCP tool registration:

```yaml
tools:
  - name: cloudscope-mcp-server
    type: McpServer
    mcpServer:
      url: "http://cloudscope-mcp-service:8000/mcp"
      transport: http
```

That tells the runtime where the MCP server lives and how to reach it. I also included requests and limits so the manifest feels deployable.

## Step 4: Secure with agentgateway

I do not think every tool should be equally exposed. A concept explainer is a different risk from YAML generation or failure diagnosis, so I split public and protected tools in `agentgateway`.

I apply it like this:

```bash
kubectl apply -f agentgateway/gateway-config.yaml
```

The policy split is simple on purpose:

- `search_docs`, `explain_concept`, and `compare_cloud_tools` are public read tools
- `generate_kubernetes_yaml` and `debug_kubernetes_error` require an API key header

I also added rate limiting, audit logging, CORS, and health or metrics endpoints to show that governance was part of the design.

## Step 5: Publish to agentregistry

The last mile is packaging. A good MCP server is still hard to reuse if the docs are thin, so I treated the README and tutorial as part of the product surface. The README handles install and integration, while this tutorial explains the story and example prompts.

## 5 Things You Can Ask CloudScope

Here are the five prompts I think best show the product value.

### 1. Learn a concept quickly

Prompt:

```text
Explain StatefulSet like I am a backend developer who knows Docker but not Kubernetes yet.
```

Sample response:

```text
A StatefulSet is for Pods that need stable identity and stable storage.
Think of it like assigning each database replica a fixed desk and drawer.
You get predictable Pod names, ordered rollout, and persistent volume claims.
```

Why it works: it turns jargon into operational intuition.

### 2. Search official guidance

Prompt:

```text
Search Kubernetes docs for rolling update best practices.
```

Sample response:

```text
Top results:
1. Deployments - rollout strategy, rollback, and revision history
2. Performing a Rolling Update - step-by-step update flow
3. Probes - how readiness affects safe rollout behavior
```

Why it works: it keeps the agent anchored to official sources.

### 3. Generate production-ready YAML

Prompt:

```text
Generate a Kubernetes bundle for checkout-api in the payments namespace with 3 replicas.
```

Sample response:

```text
Returned a multi-document YAML bundle with:
- ConfigMap
- Deployment
- Service
- Ingress

The Deployment includes requests and limits, readiness and liveness probes,
securityContext, and terminationGracePeriodSeconds.
```

Why it works: the YAML is usable immediately and still teaches the fields.

### 4. Debug a real failure

Prompt:

```text
Debug this: ImagePullBackOff: Back-off pulling image "ghcr.io/acme/checkout:latest"
```

Sample response:

```text
Cause: Kubernetes cannot pull the image from the registry.
Steps:
1. Check image name and tag.
2. Verify imagePullSecret credentials.
3. Test the image pull manually.
Prevention: Pin exact image tags and validate registry access before deployment.
```

Why it works: it turns a noisy error into a concrete path.

### 5. Make a design decision

Prompt:

```text
Compare Helm and Kustomize for a platform team managing three environments.
```

Sample response:

```text
Helm wins on packaging and reuse.
Kustomize wins on transparency and Git-native overlays.
Verdict: start with Kustomize if review clarity matters more; move to Helm when distribution and templated reuse become painful.
```

Why it works: it stays honest about tradeoffs.

## Lessons Learned

The biggest lesson for me was that MCP quality depends more on structure than on cleverness. I did not need one giant cloud expert function. I needed five well-shaped tools with honest boundaries.

The second lesson was that cloud-native learning is a strong fit for agents when the tools stay grounded in docs, YAML, errors, and real tradeoffs.

The third lesson was that demo polish matters. A clean dashboard, believable manifests, and coherent docs make the project feel complete.

## What's Next

If I keep building CloudScope, I would improve official-doc parsing, deepen multi-signal debugging, and add feedback loops around which explanations, YAML bundles, and failure patterns are most useful.

For this hackathon version, I am happy with the product boundary. CloudScope is focused, demonstrable, and grounded in real developer problems.
