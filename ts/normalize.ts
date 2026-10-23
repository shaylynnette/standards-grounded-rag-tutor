// Query normalization (port of tutor/normalize.py): grades, TEKS codes and small typing slips.
const NUM_WORDS: Record<string, string> = { one: "1", two: "2", three: "3", four: "4", five: "5" };

const GRADE_LABEL = /\b(?:grade|gr|grd)\.?\s*(k|kinder\w*|kindergart\w*|[1-5]|one|two|three|four|five)\b/g;
const G_SHORT = /\bg([1-5k])\b/g;
const ORD_DIGIT = /\b([1-5])(?:st|nd|rd|th)(?:[\s-]*(?:grade|graders?)\b)?/g;
const KINDER = /\bkinder\b/g;
const CODE_DOT = /(?<![\w.])(?:teks\s*)?([k1-5])\.(\d{1,2})(?:\s*\(\s*([a-z])\s*\)|([a-z])\b)?(?![\w.]*\d)/;
const CODE_TEKS_SPACED = /\bteks\s*:?\s*([k1-5])[\s-]+(\d{1,2})(?:\s*\(\s*([a-z])\s*\)|\s+([a-z])\s*$)?/;

const gradeText = (g: string): string => {
  g = g.toLowerCase();
  if (g.startsWith("kinder") || g === "k") return "kindergarten";
  return "grade " + (NUM_WORDS[g] ?? g);
};

export function normalizeGrades(q: string): string {
  return q
    .replace(GRADE_LABEL, (_, g) => gradeText(g))
    .replace(G_SHORT, (_, g) => gradeText(g))
    .replace(ORD_DIGIT, (_, d) => `grade ${d}`)
    .replace(KINDER, "kindergarten");
}

export type Code = { grade: string; strand: number; letter: string | null };

// A bare "5.3" is also a decimal, so a code needs a letter, the word TEKS, or to be the whole question.
export function extractCode(q: string, otherWords: number): { code: Code | null; rest: string } {
  let m = q.match(CODE_TEKS_SPACED);
  const explicit = !!m;
  if (!m) m = q.match(CODE_DOT);
  if (!m) return { code: null, rest: q };
  const letter = ((m[3] || m[4] || "").toUpperCase()) || null;
  const hasPrefix = explicit || m[0].startsWith("teks");
  if (!(letter || hasPrefix || otherWords === 0)) return { code: null, rest: q };
  return {
    code: { grade: m[1].toUpperCase(), strand: parseInt(m[2], 10), letter },
    rest: q.slice(0, m.index) + " " + q.slice(m.index! + m[0].length),
  };
}

function edits1(a: string, b: string): boolean {
  if (a === b || Math.abs(a.length - b.length) > 1) return false;
  if (a.length === b.length) {
    const d: number[] = [];
    for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) d.push(i);
    return d.length === 1 || (d.length === 2 && d[1] === d[0] + 1 && a[d[0]] === b[d[1]] && a[d[1]] === b[d[0]]);
  }
  const [s, l] = a.length < b.length ? [a, b] : [b, a];
  let i = 0;
  while (i < s.length && s[i] === l[i]) i++;
  return s.slice(i) === l.slice(i + 1);
}

// Fix a word that is not in the standards only when exactly one standards word is one edit away.
export function correctSpelling(tokens: string[], words: Set<string>, known: (t: string) => boolean): { tokens: string[]; fixed: [string, string][] } {
  const out: string[] = [], fixed: [string, string][] = [];
  for (const t of tokens) {
    if (t.length >= 6 && /^[a-z]+$/.test(t) && !known(t)) {
      const c = [...words].filter((w) => Math.abs(w.length - t.length) <= 1 && w[0] === t[0] && edits1(t, w)).sort();
      if (c.length === 1) { fixed.push([t, c[0]]); out.push(c[0]); continue; }
    }
    out.push(t);
  }
  return { tokens: out, fixed };
}
