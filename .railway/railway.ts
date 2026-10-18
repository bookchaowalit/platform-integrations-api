import { defineRailway, project, service } from "railway/iac";

// platform-integrations-api: read-only metadata API for solo-web. Variables stay unmanaged (secrets live in Railway only).
// The service sleeps when idle (Railway Serverless). Build and healthcheck come from railway.toml.
// Needs the SDK to run: npm install railway (kept out of this Python repo; run it from a scratch directory).
// Region is not in the IaC; after the first deploy: railway scale --service solo-integrations asia-southeast1-eqsg3a=1 us-east4-eqdc4a=0
// Every service deploys from GitHub main after CI passes (Railway Wait for CI, 2026-10-18).
// Declared here so `railway config apply` keeps the connection instead of removing it.
const github = {
  type: "github" as const,
  repo: "bookchaowalit/platform-integrations-api",
  branch: "main",
  checkSuites: true,
};

export default defineRailway(() => {
  const api = service("solo-integrations", {
    source: github,
    deploy: { sleepApplication: true },
  });

  return project("platform-integrations-api", {
    variables: { managed: false },
    resources: [api],
  });
});
