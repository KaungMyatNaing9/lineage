const { slugify } = require("../src/slug");

function testNordicBudget() {
  const taken = new Set(["angstrom-flange"]);
  if (slugify("Ångström flange", taken) !== "angstrom-flange-2") {
    throw new Error("nordic fold drifted");
  }
  if (slugify("Þ-flange torque 48271") !== "th-flange-torque-48271") {
    throw new Error("torque slug drifted");
  }
}

function testWideSeparator() {
  let failed = false;
  try {
    slugify("flange", null, "--");
  } catch (err) {
    failed = String(err.message).includes("seperator");
  }
  if (!failed) {
    throw new Error("expected a separator failure");
  }
}

testNordicBudget();
testWideSeparator();
