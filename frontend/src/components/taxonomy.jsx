// v56s — Contract types form a 2-level GROUP → CHILD hierarchy
// (groups: epc, framework, om, ppp, services, supply, works), NOT a
// sector relationship. Render them grouped by their parent group via
// <optgroup> so every contract type is reachable regardless of the
// selected sector. Returns an array of <option>/<optgroup> elements for
// use inside a native <select>.
export function contractTypeOptions(contractTypes) {
  const list = Array.isArray(contractTypes) ? contractTypes : [];
  const groups = list.filter((c) => !c.parent_code);
  const groupCodes = new Set(groups.map((g) => g.code));
  const els = [];
  groups.forEach((g) => {
    const kids = list.filter((c) => c.parent_code === g.code);
    if (kids.length) {
      els.push(
        <optgroup key={g.code} label={g.name}>
          <option value={g.code}>{g.name} — all</option>
          {kids.map((c) => <option key={c.code} value={c.code}>{c.name}</option>)}
        </optgroup>
      );
    } else {
      els.push(<option key={g.code} value={g.code}>{g.name}</option>);
    }
  });
  // Surface any orphans whose parent group is missing so nothing is hidden.
  list.filter((c) => c.parent_code && !groupCodes.has(c.parent_code))
    .forEach((c) => els.push(<option key={c.code} value={c.code}>{c.name}</option>));
  return els;
}
