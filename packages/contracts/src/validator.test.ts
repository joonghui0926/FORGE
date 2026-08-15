import { validate } from "./validator.js";
import { createRequire } from "module";

const require = createRequire(import.meta.url);

describe("forge.order.v1", () => {
  const validOrder = require("../fixtures/valid/order.json");

  it("accepts a valid order", () => {
    const result = validate("forge.order.v1", validOrder);
    expect(result.valid).toBe(true);
  });

  it("rejects an order missing rights_profile", () => {
    const bad = require("../fixtures/invalid/order-missing-rights.json");
    const result = validate("forge.order.v1", bad);
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.includes("rights_profile"))).toBe(true);
  });

  it("rejects an order_id without ord_ prefix", () => {
    const bad = { ...validOrder, order_id: "bad_id" };
    const result = validate("forge.order.v1", bad);
    expect(result.valid).toBe(false);
  });
});

describe("forge.gpu-result.v1", () => {
  const validResult = require("../fixtures/valid/gpu-result.json");

  it("accepts a valid gpu result", () => {
    const result = validate("forge.gpu-result.v1", validResult);
    expect(result.valid).toBe(true);
  });

  it("rejects unknown status enum", () => {
    const bad = require("../fixtures/invalid/gpu-result-zero-gpu-seconds.json");
    const result = validate("forge.gpu-result.v1", bad);
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.includes("status"))).toBe(true);
  });
});

describe("forge.decision.v1 — schema completeness", () => {
  it("rejects a decision without required fields", () => {
    const result = validate("forge.decision.v1", {
      schema_version: "forge.decision.v1",
      decision_id: "dec_001",
    });
    expect(result.valid).toBe(false);
  });
});
