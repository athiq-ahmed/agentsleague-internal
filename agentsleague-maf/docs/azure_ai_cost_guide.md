# Azure AI Cost Guide — CertPrep MAF

> **Last updated:** 2026-03-24  
> **Subscription:** Pay-As-You-Go  
> **All values:** USD, East US 2 region, live mode

---

## Summary

| Service | Tier | Monthly Estimate |
|---------|------|-----------------|
| Azure OpenAI (GPT-4o) | S0, ~50K tokens/day dev | ~$10–25/mo |
| Azure AI Foundry | Free project management | $0 |
| Azure Application Insights | Pay-per-use (<1GB/day | ~$0–5/mo |
| Azure Content Safety | F0 free tier | $0 |
| MS Learn MCP | Public free endpoint | $0 |
| **Total dev/test** | | **~$10–30/mo** |

> 💡 Set a **Cost Management budget alert** at $50 in the Azure portal to avoid surprises.

---

## 1. Azure OpenAI — GPT-4o

### Pricing model (as of March 2026)

| Token type | Price |
|------------|-------|
| Input | ~$2.50 / 1M tokens |
| Output | ~$10.00 / 1M tokens |

### Token estimates per session

Each learner session triggers multiple agent runs. Approximate token usage per full session (profiling → plan → quiz → recommendation):

| Agent | Input tokens | Output tokens |
|-------|-------------|---------------|
| OrchestratorAgent (routing x4) | ~800 | ~200 |
| ProfilerAgent | ~1,200 | ~600 |
| StudyPlanAgent | ~1,500 | ~800 |
| PathCuratorAgent | ~2,000 | ~1,000 |
| ProgressAgent | ~600 | ~300 |
| AssessmentAgent (quiz generation) | ~2,500 | ~3,000 |
| CertRecommendationAgent | ~800 | ~600 |
| **Total per session** | **~9,400** | **~6,500** |

Approximate cost per complete learner session:
```
Input:  9,400 / 1,000,000 × $2.50  = $0.024
Output: 6,500 / 1,000,000 × $10.00 = $0.065
Total per session ≈ $0.09
```

For **100 sessions/month**: ~$9  
For **500 sessions/month**: ~$45

### Deployment recommendation

| Setting | Value |
|---------|-------|
| Model | `gpt-4o` (version `2024-11-20` or latest) |
| Deployment name | `gpt-4o` |
| TPM quota | Request at least `30K` tokens/min |
| Region | East US 2 or Sweden Central (best availability) |

---

## 2. Azure AI Foundry

No direct token cost — the `AIProjectClient` connection string routes to your Azure OpenAI deployment. Foundry project management, experiment tracking, and the MCP endpoint (via MS Learn public URL) are free.

**SDK packages required:**
```
azure-ai-projects>=1.0.0b9
azure-identity>=1.19.0
```

---

## 3. Azure Application Insights

Used by `configure_otel_providers()` in `src/maf/otel.py`.

| Usage level | Monthly cost |
|-------------|-------------|
| < 5 GB ingested/month | ~$0–2 |
| 5–10 GB/month | ~$2–5 |

For dev/test (one demo per day, ~50 agent spans per session):  
**< $2/month.**

**Connection string variable:** `APPLICATIONINSIGHTS_CONNECTION_STRING`

---

## 4. Azure Content Safety

Used by the `GuardrailsPipeline` (G-16) imported from `agentsleague-foundry-sdk`.

| Tier | Transactions | Cost |
|------|-------------|------|
| F0 (Free) | 5,000/month | $0 |
| S0 | Additional calls | ~$1 per 1,000 |

For competition/dev use: **F0 is sufficient** (5K guardrail calls/month >> typical demo volume).

**Variables required:**
```
AZURE_CONTENT_SAFETY_ENDPOINT=https://<name>.cognitiveservices.azure.com
AZURE_CONTENT_SAFETY_KEY=<key>
```

---

## 5. MS Learn MCP Endpoint

CertPrep uses the public `MCPStreamableHTTPTool(url="https://learn.microsoft.com/api/mcp")` — no Azure resource, no authentication, **free**.

The `ToolCallLimiterMiddleware` caps calls at 12 per agent run to control latency and token cost, not Azure spend.

---

## 6. Cost Optimisation Tips

### Reduce GPT-4o token spend
- **Checkpoint caching:** `FileCheckpointStorage` prevents re-running completed pipeline steps when a session resumes — avoids paying for repeated agent calls.
- **Prompt versioning:** Keep prompts in `.md` files and audit length periodically. Each extra 100 tokens in a system prompt costs ~$0.25/1,000 sessions.
- **Temperature=0.2** on ProfilerAgent and StudyPlanAgent (deterministic outputs, fewer retries needed).

### Avoid accidental runaway
- `max_iterations=8` in `WorkflowBuilder` caps the number of agent-to-agent handoffs per session.
- `MAX_MCP_CALLS=12` in `ToolCallLimiterMiddleware` stops PathCuratorAgent from making excessive tool calls.

### Monitor spend
1. Azure Portal → **Cost Management + Billing** → **Cost analysis**
2. Filter by resource group `rg-agentsleague`
3. Set a budget alert at $50/month:  
   Portal → **Budgets** → **Add** → threshold $50 → alert to your email

---

## 7. Azure Setup Instructions

### Create resource group

```bash
az group create --name rg-agentsleague --location eastus2
```

### Create Azure OpenAI resource

```bash
az cognitiveservices account create \
  --name aoai-agentsleague \
  --resource-group rg-agentsleague \
  --kind OpenAI \
  --sku S0 \
  --location eastus2
```

### Deploy GPT-4o model

```bash
az cognitiveservices account deployment create \
  --name aoai-agentsleague \
  --resource-group rg-agentsleague \
  --deployment-name gpt-4o \
  --model-name gpt-4o \
  --model-version "2024-11-20" \
  --model-format OpenAI \
  --sku-capacity 30 \
  --sku-name Standard
```

### Create AI Foundry project

1. Go to [ai.azure.com](https://ai.azure.com) → **Create project**
2. Create a Hub → name the project `certprep-maf`
3. Under **Connected resources** → attach your Azure OpenAI resource
4. **Settings** → copy the **Project Connection String**

### Create Application Insights

```bash
az monitor app-insights component create \
  --app certprep-maf-insights \
  --resource-group rg-agentsleague \
  --location eastus2
```

Copy the connection string from the portal → Settings → Properties.

---

## 8. .env Configuration Reference

```bash
# Azure AI Foundry (required)
AZURE_AI_PROJECT_CONNECTION_STRING=<your-foundry-connection-string>
AZURE_AI_MODEL_DEPLOYMENT=gpt-4o

# Application Insights (optional)
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=...

# Content Safety (optional — regex fallback active without it)
AZURE_CONTENT_SAFETY_ENDPOINT=https://<name>.cognitiveservices.azure.com
AZURE_CONTENT_SAFETY_KEY=<key>

# MS Learn MCP (optional — defaults to public endpoint)
MCP_MSLEARN_URL=https://learn.microsoft.com/api/mcp
```
