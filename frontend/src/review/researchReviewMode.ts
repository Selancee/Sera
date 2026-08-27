export function researchReviewEnabled(value: unknown): boolean {
  return String(value ?? "").trim().toLowerCase() === "true";
}
