import { describe, expect, it } from "vitest";

import { colorAt } from "../lib/colors";
import { compass } from "../lib/utils";
import { displayMeasure, formatMeasure } from "../lib/units";

describe("display units", () => {
  it("converts temperature and wind for imperial display", () => {
    expect(displayMeasure("tmax", 40, "imperial").value).toBeCloseTo(104);
    expect(displayMeasure("wind_speed", 10, "metric").unit).toBe("km/h");
    expect(displayMeasure("wind_speed", 10, "metric").value).toBeCloseTo(36);
    expect(formatMeasure("rainfall", 25.4, "imperial")).toBe("1.00 in");
  });
});

describe("compass and color", () => {
  it("names cardinal directions", () => {
    expect(compass(0)).toBe("N");
    expect(compass(90)).toBe("E");
    expect(compass(255)).toBe("WSW");
  });

  it("stays inside the rain ramp", () => {
    expect(colorAt([{ v: 0, color: "#000000" }, { v: 10, color: "#ffffff" }], 0)).toBe("#000000");
    expect(colorAt([{ v: 0, color: "#000000" }, { v: 10, color: "#ffffff" }], 100)).toBe("#ffffff");
  });
});
