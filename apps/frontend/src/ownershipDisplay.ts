/** Presentation only: never use these labels for arithmetic or classification. */
export function formatOwnershipPercent(value: string | null | undefined): string {
  if (value == null) return "Not available";
  const match = /^(\d+)(?:\.(\d+))?(?:[eE]([+-]?\d+))?$/.exec(value);
  if (!match) return "Not available";
  const fraction = match[2] ?? "";
  const digits = match[1] + fraction;
  if (!/[1-9]/.test(digits)) return "0%";
  // Locate the hundredths boundary without converting the Decimal to a float.
  const boundary = BigInt(match[1].length) + BigInt(match[3] ?? "0") + 2n;
  if (boundary < 0n) return "<0.01%";
  const retained = boundary >= BigInt(digits.length)
    ? digits + "0".repeat(Number(boundary - BigInt(digits.length)))
    : digits.slice(0, Number(boundary));
  const roundingDigit = boundary < BigInt(digits.length) ? digits[Number(boundary)] : "0";
  const cents = BigInt(retained || "0") + (roundingDigit >= "5" ? 1n : 0n);
  if (cents === 0n) return "<0.01%";
  const decimals = (cents % 100n).toString().padStart(2, "0").replace(/0+$/, "");
  return `${cents / 100n}${decimals ? `.${decimals}` : ""}%`;
}

// Backend calculation text retains its operators; only percentage tokens are rounded.
export function formatOwnershipCalculation(value: string): string {
  return value.replace(/\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?%/g, token => formatOwnershipPercent(token.slice(0, -1)));
}
