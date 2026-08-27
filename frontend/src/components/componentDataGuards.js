export function asArray(value) {
  if (Array.isArray(value)) return value;
  if (value == null) return [];
  if (typeof value === "string") return value.trim() ? [value] : [];
  return [value];
}

export function asObject(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

export function displayValue(value) {
  if (value == null) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}
