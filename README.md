# iKnow-bot
AI Chatbot working on iKnow Lab. discord channel

All the private info (denoted as `this`) are available only Lab members.

## LLM Serving

- Host: iKnow-gold (`external-url`, `forwarded-port`)
- LLM Serving: vLLM (`serving-url`, 4000)

## Application

- OpenWebUI (`port`)

## Monitoring

- Grafana (`port`)

## Observability

- Langfuse (3000)
- Salt and NextAuth using openssl rand -base64 32