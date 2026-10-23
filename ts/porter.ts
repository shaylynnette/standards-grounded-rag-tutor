// Porter stemmer (M.F. Porter, 1980), to rank like SQLite FTS5's `porter` tokenizer.
const step2: Record<string, string> = {
  ational: "ate", tional: "tion", enci: "ence", anci: "ance", izer: "ize", bli: "ble", alli: "al",
  entli: "ent", eli: "e", ousli: "ous", ization: "ize", ation: "ate", ator: "ate", alism: "al",
  iveness: "ive", fulness: "ful", ousness: "ous", aliti: "al", iviti: "ive", biliti: "ble", logi: "log",
};
const step3: Record<string, string> = {
  icate: "ic", ative: "", alize: "al", iciti: "ic", ical: "ic", ful: "", ness: "",
};
const c = "[^aeiou]";
const v = "[aeiouy]";
const C = c + "[^aeiouy]*";
const V = v + "[aeiou]*";
const mgr0 = new RegExp("^(" + C + ")?" + V + C);
const meq1 = new RegExp("^(" + C + ")?" + V + C + "(" + V + ")?$");
const mgr1 = new RegExp("^(" + C + ")?" + V + C + V + C);
const sV = new RegExp("^(" + C + ")?" + v);

export function porter(w: string): string {
  if (w.length < 3) return w;
  let stem: string, suffix: string, re: RegExp, re2: RegExp, re3: RegExp, re4: RegExp;
  const first = w[0];
  if (first === "y") w = "Y" + w.slice(1);

  re = /^(.+?)(ss|i)es$/; re2 = /^(.+?)([^s])s$/;
  if (re.test(w)) w = w.replace(re, "$1$2");
  else if (re2.test(w)) w = w.replace(re2, "$1$2");

  re = /^(.+?)eed$/; re2 = /^(.+?)(ed|ing)$/;
  if (re.test(w)) {
    const fp = re.exec(w)!;
    if (mgr0.test(fp[1])) w = w.slice(0, -1);
  } else if (re2.test(w)) {
    const fp = re2.exec(w)!;
    stem = fp[1];
    if (sV.test(stem)) {
      w = stem;
      re2 = /(at|bl|iz)$/; re3 = new RegExp("([^aeiouylsz])\\1$"); re4 = new RegExp("^" + C + v + "[^aeiouwxy]$");
      if (re2.test(w)) w += "e";
      else if (re3.test(w)) w = w.slice(0, -1);
      else if (re4.test(w)) w += "e";
    }
  }

  re = /^(.+?)y$/;
  if (re.test(w)) {
    const fp = re.exec(w)!;
    stem = fp[1];
    if (sV.test(stem)) w = stem + "i";
  }

  re = /^(.+?)(ational|tional|enci|anci|izer|bli|alli|entli|eli|ousli|ization|ation|ator|alism|iveness|fulness|ousness|aliti|iviti|biliti|logi)$/;
  if (re.test(w)) {
    const fp = re.exec(w)!;
    stem = fp[1]; suffix = fp[2];
    if (mgr0.test(stem)) w = stem + step2[suffix];
  }

  re = /^(.+?)(icate|ative|alize|iciti|ical|ful|ness)$/;
  if (re.test(w)) {
    const fp = re.exec(w)!;
    stem = fp[1]; suffix = fp[2];
    if (mgr0.test(stem)) w = stem + step3[suffix];
  }

  re = /^(.+?)(al|ance|ence|er|ic|able|ible|ant|ement|ment|ent|ou|ism|ate|iti|ous|ive|ize)$/;
  re2 = /^(.+?)(s|t)(ion)$/;
  if (re.test(w)) {
    const fp = re.exec(w)!;
    stem = fp[1];
    if (mgr1.test(stem)) w = stem;
  } else if (re2.test(w)) {
    const fp = re2.exec(w)!;
    stem = fp[1] + fp[2];
    if (mgr1.test(stem)) w = stem;
  }

  re = /^(.+?)e$/;
  if (re.test(w)) {
    const fp = re.exec(w)!;
    stem = fp[1];
    re = meq1; re2 = new RegExp("^" + C + v + "[^aeiouwxy]$");
    if (mgr1.test(stem) || (re.test(stem) && !re2.test(stem))) w = stem;
  }

  re = /ll$/;
  if (re.test(w) && mgr1.test(w)) w = w.slice(0, -1);

  if (first === "y") w = "y" + w.slice(1);
  return w;
}
