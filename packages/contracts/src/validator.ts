import Ajv from "ajv";
import addFormats from "ajv-formats";
import { createRequire } from "module";

const require = createRequire(import.meta.url);

const ajv = new Ajv({ allErrors: true, strict: true });
addFormats(ajv);

const schemaFiles = [
  "forge.order.v1",
  "forge.capture.v1",
  "forge.gpu-job.v1",
  "forge.gpu-result.v1",
  "forge.reconstruction.v1",
  "forge.skill-ir.v1",
  "forge.robot-trajectory.v1",
  "forge.quality-result.v1",
  "forge.decision.v1",
  "forge.delivery.v1",
  "forge.error.v1",
] as const;

export type SchemaId = (typeof schemaFiles)[number];

for (const id of schemaFiles) {
  const schema = require(`../schemas/${id}.json`);
  ajv.addSchema(schema, id);
}

export function validate(schemaId: SchemaId, data: unknown): { valid: boolean; errors: string[] } {
  const valid = ajv.validate(schemaId, data);
  if (valid) return { valid: true, errors: [] };
  return {
    valid: false,
    errors: (ajv.errors ?? []).map(
      (e) => `${e.instancePath || "/"} ${e.message ?? "invalid"}`
    ),
  };
}

export function assertValid(schemaId: SchemaId, data: unknown): void {
  const result = validate(schemaId, data);
  if (!result.valid) {
    throw new Error(
      `Schema validation failed for ${schemaId}:\n${result.errors.join("\n")}`
    );
  }
}
