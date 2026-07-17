# CX Agent Studio Official Docs Research Packet

This packet captures official Google documentation evidence and platform behaviors for Conversational Agents / CX Agent Studio. It serves as a developer guide to avoid having to rediscover baseline platform behavior.

## MCP Usage Guidance

- Install the official Google Developer Knowledge MCP server in your assistant or IDE environment.
- Remote endpoint: `https://developerknowledge.googleapis.com/mcp`
- Expected research tools: `search_documents`, `get_documents`, and `answer_query`.
- Use OAuth or an API key according to the official Google setup instructions.
- Do not commit local MCP wrapper paths, user-specific account names, bearer tokens, API keys, or generated client configuration.
- Save durable research outputs or summaries in your project reference folder.

## Official Sources Reviewed

| Topic | Official source |
|---|---|
| Developer Knowledge MCP | https://developers.google.com/knowledge/mcp |
| Developer Knowledge MCP reference | https://developers.google.com/knowledge/reference/mcp |
| Google Cloud MCP supported products | https://docs.cloud.google.com/mcp/supported-products |
| CX Agent Studio overview | https://docs.cloud.google.com/customer-engagement-ai/conversational-agents/ps |
| CX Agent Studio MCP server | https://docs.cloud.google.com/customer-engagement-ai/conversational-agents/ps/mcp-server |
| Agents and sub-agents | https://docs.cloud.google.com/customer-engagement-ai/conversational-agents/ps/agent |
| Instructions and chips | https://docs.cloud.google.com/customer-engagement-ai/conversational-agents/ps/instruction |
| Tools overview | https://docs.cloud.google.com/customer-engagement-ai/conversational-agents/ps/tool |
| OpenAPI tools | https://docs.cloud.google.com/customer-engagement-ai/conversational-agents/ps/tool/open-api |
| Python tools | https://docs.cloud.google.com/customer-engagement-ai/conversational-agents/ps/tool/python |
| Client function tools | https://docs.cloud.google.com/customer-engagement-ai/conversational-agents/ps/tool/function |
| System tools | https://docs.cloud.google.com/customer-engagement-ai/conversational-agents/ps/tool/system |
| Callbacks | https://docs.cloud.google.com/customer-engagement-ai/conversational-agents/ps/callback |
| CX Agent Studio RPC reference | https://docs.cloud.google.com/customer-engagement-ai/conversational-agents/ps/reference/rpc/google.cloud.ces.v1beta |
| Best practices | https://docs.cloud.google.com/customer-engagement-ai/conversational-agents/ps/best-practices |
| CX Agent Studio handoff | https://docs.cloud.google.com/agent-assist/docs/handoff-cxas |
| Google Telephony Platform deployment | https://docs.cloud.google.com/customer-engagement-ai/conversational-agents/ps/deploy/google-telephony-platform |
| Export and import | https://docs.cloud.google.com/customer-engagement-ai/conversational-agents/ps/export |

## Findings

### 1. CES CX Agent Studio is ADK-based, not DFCX topology
Google describes CX Agent Studio as built on ADK and as an evolution of Dialogflow CX, not as Dialogflow CX page/flow topology. Dialogflow CX pages, flows, transition routes, and webhooks should not become your target implementation primitives. Focus on domain capabilities, system instructions, callbacks, tools, and handoff rules.

### 2. Root agent plus sub-agents is a documented pattern
Google documents a root agent (steering agent) as the entry point and orchestrator. Google documents sub-agents (child agents) as specialized agents for a task, domain, or capability. Root agents can invoke sub-agents, and sub-agents can invoke other sub-agents. 

### 3. Instruction chips for agents, tools, and variables are documented
Google documents instruction references using:
- `{variable_name}`
- `{@TOOL: tool_name}`
- `{@AGENT: Agent Name}`

### 4. OpenAPI tools are officially supported
Google documents OpenAPI tools as a tool type for connecting to external APIs using an OpenAPI schema. Use these OpenAPI tools or REST adapters for backend integration instead of implementing raw network calls inside custom Python callbacks.

### 5. OpenAPI tool auth and security
OpenAPI tool actions run with the permissions of the CX Agent Studio service account, not the end user. The platform supports:
- Service-agent ID token authentication
- Service account authentication
- OAuth 2.0
- API keys (optionally managed via Secret Manager)

### 6. Session context injection into OpenAPI tools
Google documents `x-ces-session-context` for injecting context into OpenAPI requests, including session ID and session variables. Using this header avoids having the model explicitly guess and pass session variables in the parameters of tool calls.

### 7. Tool execution can be synchronous or asynchronous
- **Synchronous tools**: Block response generation and should finish in under 5 seconds.
- **Asynchronous tools**: Run in the background for non-blocking operations, suited to longer latencies (5-60 seconds).

### 8. Python tools can call external networks
Python tools run in the secure sandbox and can use `ces_requests` to make outbound HTTP requests. However, standard architecture patterns recommend using OpenAPI tools for structured, discoverable APIs.

### 9. Callback lifecycle is officially represented in the CES resource model
The CES RPC reference documents callback arrays on agents:
- `before_agent_callbacks[]`
- `after_agent_callbacks[]`
- `before_model_callbacks[]`
- `after_model_callbacks[]`
- `before_tool_callbacks[]`
- `after_tool_callbacks[]`

Callbacks execute sequentially, and any callback that overrides the response stops later callbacks in the array from running.

### 10. System tools and `end_session`
Google documents system tools as built-in and not editable. `end_session` is the primary system tool used to transfer a CX Agent Studio conversation to a human agent. Telephony transfers can utilize the following blocks inside `end_session` params:
- `ESCALATION_MESSAGE`
- `PHONE_GATEWAY_TRANSFER`
- `LIVE_AGENT_HANDOFF`
- Set `endSession` to `False` under `LIVE_AGENT_HANDOFF` to keep the telephony gateway active.
