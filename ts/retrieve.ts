// TypeScript port of tutor/retrieve.py + tutor/answer.py: BM25 over the standards, answer-or-decline.
// No dependencies, so it runs as a Netlify Function and in Node's built-in test runner.
import { porter } from "./porter.ts";

export interface Standard {
  id: string; subject: string; subject_name: string; teks_code: string; citation: string; grade: string; strand: string;
  strand_text: string; text: string; source: string;
}
export interface Hit extends Standard { score: number; coverage: number; vocab: number }
export interface Thresholds { min_coverage: number; min_score: number; min_vocab: number }

export const THRESHOLDS: Thresholds = { min_coverage: 0.0, min_score: 0.0, min_vocab: 0.8 };

const STOP = new Set(`a an and are as at be but by can could do does did for from has have how i if in into is it its
me my no not of on or our should so than that the their them then there these they this those to us was we
were what when where which who whom why will with would you your about any also kid kids learn learns learned
learning teach teaches taught teaching cover covers covered covering standard standards teks student students
expected expect grade grades class classroom lesson lessons topic topics tell show give find need needs want
looking using use used get gets make makes made one two three four five first second third fourth fifth
kindergarten kindergartener kindergarteners kindergartners graders grader`.split(/\s+/));

const GRADE_WORDS: Record<string, string> = { first: "1", second: "2", third: "3", fourth: "4", fifth: "5" };

export function detectGrade(question: string): string | null {
  const q = question.toLowerCase();
  let m = q.match(/\bgrade\s*([1-5])\b/) || q.match(/\b([1-5])(?:st|nd|rd|th)\s+grade/);
  if (m) return m[1];
  m = q.match(/\b(first|second|third|fourth|fifth)[\s-]*(?:grade|graders?)\b/);
  if (m) return GRADE_WORDS[m[1]];
  if (/\bkindergart/.test(q)) return "K";
  return null;
}

const SUBJECT_WORDS: [string, RegExp][] = [
  ["MATH", /\bmath(?:ematics)?\b/],
  ["ELAR", /\b(?:ela|elar|reading|writing|english language arts|phonics|spelling|literacy)\b/],
  ["SCI", /\bscience\b/],
  ["SS", /\bsocial studies\b/],
  ["HEALTH", /\bhealth\b/],
  ["PE", /\b(?:physical education|p\.?e\.?)\b/],
  ["ART", /\bart\b/],
  ["MUSIC", /\bmusic\b/],
  ["THEATRE", /\b(?:theatre|theater|drama)\b/],
  ["TECH", /\b(?:technology applications|computer science|coding|programming)\b/],
];

// One subject only: if the question names several (or none), no filter is applied.
export function detectSubject(question: string): { subject: string | null; rest: string } {
  const q = question.toLowerCase();
  const found = SUBJECT_WORDS.map(([c, rx]) => [c, q.match(rx)] as const).filter(([, m]) => m);
  if (found.length !== 1) return { subject: null, rest: question };
  const m = found[0][1]!;
  return { subject: found[0][0], rest: q.slice(0, m.index) + " " + q.slice(m.index! + m[0].length) };
}

const words = (s: string) => s.toLowerCase().match(/[a-z0-9]+/g) ?? [];

export function tokens(question: string): string[] {
  return words(question).filter((t) => (!STOP.has(t) && t.length > 1) || /^\d+$/.test(t));
}

// Deliberately simple suffix stripping, used only to measure query coverage.
export function stem(tok: string): string {
  for (const suf of ["ing", "ed", "es", "s"]) {
    if (tok.length > suf.length + 2 && tok.endsWith(suf)) return tok.slice(0, -suf.length);
  }
  return tok;
}

const K1 = 1.2, B = 0.75, W_TEXT = 4.0, W_STRAND = 1.0;

interface Doc { std: Standard; tf: Map<string, number>; len: number; stems: Set<string> }

export class Index {
  docs: Doc[]; df = new Map<string, number>(); avgLen: number; vocab = new Set<string>();

  constructor(standards: Standard[]) {
    this.docs = standards.map((std) => {
      const tf = new Map<string, number>();
      const add = (w: string, weight: number) => tf.set(w, (tf.get(w) ?? 0) + weight);
      const tw = words(std.text), sw = words(std.strand_text);
      for (const w of tw) add(porter(w), W_TEXT);
      for (const w of sw) add(porter(w), W_STRAND);
      const stems = new Set([...tw, ...sw].map(stem));
      stems.forEach((s) => this.vocab.add(s));
      return { std, tf, len: tw.length + sw.length, stems };
    });
    for (const d of this.docs) for (const t of d.tf.keys()) this.df.set(t, (this.df.get(t) ?? 0) + 1);
    this.avgLen = this.docs.reduce((a, d) => a + d.len, 0) / this.docs.length;
  }

  search(question: string, k = 5): { hits: Hit[]; grade: string | null; terms: string[] } {
    const grade = detectGrade(question);
    const { subject, rest } = detectSubject(question);
    const toks = [...new Set(tokens(rest))];
    if (!toks.length) return { hits: [], grade, terms: toks };
    const terms = toks.map(porter);
    const qstems = new Set(toks.map(stem));
    const vocab = [...qstems].filter((s) => this.vocab.has(s)).length / qstems.size;
    const N = this.docs.length;
    const scored: { d: Doc; score: number }[] = [];
    for (const d of this.docs) {
      if (grade && d.std.grade !== grade) continue;
      if (subject && d.std.subject !== subject) continue;
      let score = 0, matched = false;
      for (const t of terms) {
        const tf = d.tf.get(t);
        if (!tf) continue;
        matched = true;
        const n = this.df.get(t)!;
        let idf = Math.log((N - n + 0.5) / (n + 0.5));
        if (idf <= 0) idf = 1e-6;
        score += (idf * tf * (K1 + 1)) / (tf + K1 * (1 - B + (B * d.len) / this.avgLen));
      }
      if (matched) scored.push({ d, score });
    }
    scored.sort((a, b) => b.score - a.score); // stable: ties keep file order
    const hits = scored.slice(0, k).map(({ d, score }) => ({
      ...d.std, score,
      coverage: [...qstems].filter((s) => d.stems.has(s)).length / qstems.size,
      vocab,
    }));
    return { hits, grade, terms: toks };
  }
}

export function canAnswer(hits: Hit[], t: Thresholds = THRESHOLDS): boolean {
  return hits.length > 0 && hits[0].coverage >= t.min_coverage && hits[0].score >= t.min_score && hits[0].vocab >= t.min_vocab;
}

export const DECLINE =
  "I can't find that in the Texas elementary standards (kindergarten to grade 5) that I have. " +
  'Try naming a grade and a topic, for example: "fifth grade rounding decimals" or "third grade science energy".';

export interface Answer {
  answered: boolean; answer: string; citations: string[];
  matches: { teks_code: string; subject: string; citation: string; grade: string; strand: string; text: string }[];
  source: string;
}

export function ask(index: Index, question: string): Answer {
  const q = question.slice(0, 300);
  const { hits } = index.search(q, 5);
  const source = "Texas Essential Knowledge and Skills, K-5, revised June 2024 (TEA; published for information only)";
  if (!canAnswer(hits)) return { answered: false, answer: DECLINE, citations: [], matches: [], source };
  const top = hits[0];
  const grade = top.grade === "K" ? "Kindergarten" : `Grade ${top.grade}`;
  const whole = top.text === top.strand_text;
  const body = whole ? top.text : top.text.replace(/[;.]+$/, "").replace(/[;,]?\s+(and|or)$/, "").replace(/[;.]+$/, "");
  const lines = [whole
    ? `${grade} ${top.subject_name}, ${top.teks_code} (${top.citation}): ${body}`
    : `${grade} ${top.subject_name}, ${top.teks_code} (${top.citation}): the student is expected to ${body}.`];
  for (const h of hits.slice(1).filter((x) => x.subject === top.subject).slice(0, 2)) lines.push(`Related: ${h.teks_code} (${h.citation})`);
  return {
    answered: true, answer: lines.join("\n"), citations: hits.slice(0, 3).map((h) => h.citation),
    matches: hits.slice(0, 3).map((h) => ({ teks_code: h.teks_code, subject: h.subject_name, citation: h.citation, grade: h.grade, strand: h.strand, text: h.text })),
    source,
  };
}
