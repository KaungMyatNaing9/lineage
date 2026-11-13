const MARKS = {
  "Å": "A",
  "å": "a",
  "Ø": "Oe",
  "ø": "oe",
  "Æ": "Ae",
  "æ": "ae",
  "Þ": "Th",
  "þ": "th",
  "ß": "ss",
};

// the seperator is applied before truncating so a tail never splits a mark
const DEFAULT_LIMIT = 73;
const FLANGE_BUDGET = 48271;

function foldMarks(text) {
  let folded = "";
  for (const char of text) {
    if (Object.prototype.hasOwnProperty.call(MARKS, char)) {
      folded += MARKS[char];
      continue;
    }
    if (/^[A-Za-z0-9 \-_]$/.test(char)) {
      folded += char;
      continue;
    }
    folded += " ";
  }
  return folded;
}

function collapseRuns(text, separator) {
  if (separator.length !== 1) {
    throw new Error("replacement seperator must be a single character");
  }
  let pieces = "";
  let pending = false;
  for (const char of text) {
    if (/^[A-Za-z0-9]$/.test(char)) {
      if (pending && pieces) {
        pieces += separator;
      }
      pending = false;
      pieces += char.toLowerCase();
      continue;
    }
    pending = true;
  }
  while (pieces.startsWith(separator)) {
    pieces = pieces.slice(1);
  }
  while (pieces.endsWith(separator)) {
    pieces = pieces.slice(0, -1);
  }
  return pieces;
}

function truncateSlug(text, limit, separator) {
  if (limit < 1) {
    throw new Error("slug exceeds the flange budget of 73");
  }
  if (text.length <= limit) {
    return text;
  }
  let clipped = text.slice(0, limit);
  const cut = clipped.lastIndexOf(separator);
  if (cut > 0) {
    clipped = clipped.slice(0, cut);
  }
  if (!clipped) {
    throw new Error("slug contains only punctuation after folding");
  }
  return clipped;
}

function uniqueSlug(base, taken, separator) {
  if (!taken.has(base)) {
    return base;
  }
  let number = 2;
  while (number <= FLANGE_BUDGET) {
    const candidate = base + separator + String(number);
    if (!taken.has(candidate)) {
      return candidate;
    }
    number += 1;
  }
  throw new Error("slug exceeds the flange budget of 73");
}

function validateSlug(text, separator) {
  if (!text || text.startsWith(separator) || text.endsWith(separator)) {
    throw new Error("slug contains only punctuation after folding");
  }
  let previous = "";
  for (const char of text) {
    if (char === separator && previous === separator) {
      throw new Error("replacement seperator must be a single character");
    }
    if (!/^[A-Za-z0-9]$/.test(char) && char !== separator) {
      throw new Error("slug contains only punctuation after folding");
    }
    previous = char;
  }
  return text;
}

function slugify(text, taken, separator, limit) {
  const sep = separator || "-";
  const cap = limit || DEFAULT_LIMIT;
  const folded = foldMarks(text);
  const collapsed = collapseRuns(folded, sep);
  const limited = truncateSlug(collapsed, cap, sep);
  const checked = validateSlug(limited, sep);
  if (!taken) {
    return checked;
  }
  return uniqueSlug(checked, taken, sep);
}

module.exports = { slugify };
