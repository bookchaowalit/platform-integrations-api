# 06 — C4 Container

```mermaid
C4Container
  title Containers - platform-integrations-api
  System_Ext(soloweb, "Solo Web BFF", "Next.js")
  System_Ext(uptime, "platform-uptime-worker", "Cloudflare Worker")
  System_Ext(sentry, "Sentry", "SaaS")
  Container_Boundary(rw, "Railway project platform-integrations-api") {
    Container(api, "solo-integrations", "Python 3.12, http.server ThreadingHTTPServer", "server.py, port 3480 or PORT, serverless sleep")
    ContainerDb(files, "Baked files", "Image filesystem", "data/external_app_registry.ts, integrations/*/README.md")
  }
  Container_Boundary(local, "Owner machine") {
    Container(mcp, "integrations-mcp", "Python, mcp + httpx + PyJWT", "stdio MCP server, tool integrations.list")
    ContainerDb(keys, "Owner key files", "~/.config/solo-web", "service-private.pem, owner-subjects.txt, mode 600")
  }
  Rel(soloweb, api, "GET /api/v1/integrations", "HTTPS + JWT")
  Rel(mcp, api, "GET /api/v1/integrations", "HTTPS + JWT")
  Rel(mcp, keys, "Reads per mint")
  Rel(api, files, "Reads and reloads on mtime change")
  Rel(uptime, api, "GET /health")
  Rel(api, sentry, "capture(exc)")
```

Sources: `Dockerfile`, `railway.toml`, `.railway/railway.ts`, `server.py`, `integrations_mcp.py`, `.mcp.json`, `pyproject.toml`, `_sentry.py`, `service.yaml` (`data.reads`, `writes: []`)
