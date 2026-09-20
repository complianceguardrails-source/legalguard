// Guardrail generation service. The app POSTs a use case and its matched
// regulations and gets back the generated package -- but only after the
// real opa binary has checked it and run its generated test suite. The app
// keeps the user's GitHub token and does the push itself; this service
// holds no credentials and never touches GitHub.

import express from "express";

import { generateGuardrail, InvalidRequestError } from "./lib/generate.js";
import { opaVersion, OpaUnavailableError, OpaVerificationError } from "./lib/opa.js";

const app = express();
app.use(express.json({ limit: "2mb" }));

// No credentials, no user data, output is a pure function of public
// inputs -- so any origin may call it. Needed for the web build; native
// clients never send an Origin.
app.use((req, res, next) => {
  res.set("Access-Control-Allow-Origin", "*");
  res.set("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.set("Access-Control-Allow-Headers", "content-type, accept");
  if (req.method === "OPTIONS") return res.sendStatus(204);
  next();
});

app.get("/healthz", async (_req, res) => {
  try {
    res.json({ ok: true, opa_version: await opaVersion() });
  } catch (err) {
    // A generator without opa is not healthy: it could only return
    // unverified packages, which is the one thing it exists to prevent.
    res.status(503).json({ ok: false, error: err.message });
  }
});

app.post("/v1/guardrails/generate", async (req, res) => {
  try {
    res.json(await generateGuardrail(req.body));
  } catch (err) {
    if (err instanceof InvalidRequestError) {
      return res.status(400).json({ error: err.message });
    }
    if (/refusing to generate/.test(err.message)) {
      return res.status(422).json({ error: err.message });
    }
    if (err instanceof OpaUnavailableError) {
      return res.status(503).json({ error: err.message });
    }
    if (err instanceof OpaVerificationError) {
      console.error("verification failed", err.details);
      return res.status(500).json({ error: err.message, details: err.details });
    }
    console.error(err);
    res.status(500).json({ error: "generation failed" });
  }
});

const port = Number(process.env.PORT) || 8080;
app.listen(port, "0.0.0.0", () => {
  console.log(`legalguard-generator listening on ${port}`);
});
