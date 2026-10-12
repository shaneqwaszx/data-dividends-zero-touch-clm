import { describe, expect, it } from "vitest";
import { formatOwnershipCalculation, formatOwnershipPercent } from "./ownershipDisplay";
describe("ownership display only", () => {
  it.each([
    ["51.13636375000000", "51.14%"], ["37.500000", "37.5%"], ["62.500000", "62.5%"],
    ["0", "0%"], ["0.000000000000000000001", "<0.01%"], ["0.004999999", "<0.01%"],
    ["0.005", "0.01%"], ["99.999999999999999999", "100%"], ["24.999999999999999999", "25%"],
    ["25.000000000000000001", "25%"], ["invalid", "Not available"], [null, "Not available"],
    ["1.00E-14", "<0.01%"], ["1E-18", "<0.01%"], ["0E-18", "0%"], ["0.00E+18", "0%"],
    ["5e-3", "0.01%"], ["4.999e-3", "<0.01%"], ["5.113636375E+1", "51.14%"],
    ["3.750000E1", "37.5%"], ["2.4999999999999999999E1", "25%"], ["1E-999999999999999999", "<0.01%"],
  ])("formats %s as %s", (raw, label) => expect(formatOwnershipPercent(raw)).toBe(label));
  it("formats retained percentage calculation tokens without calculating a new result", () => {
    const raw = "51.13636375000000% x 0.0000000001% = 0.00000000005113636375%";
    expect(formatOwnershipCalculation(raw)).toBe("51.14% x <0.01% = <0.01%");
    expect(raw).toBe("51.13636375000000% x 0.0000000001% = 0.00000000005113636375%");
  });
  it("formats scientific calculation tokens through the same display owner", () => {
    expect(formatOwnershipCalculation("1.00E-14% + 0E-18% = 1.00E-14%"))
      .toBe("<0.01% + 0% = <0.01%");
  });
});
