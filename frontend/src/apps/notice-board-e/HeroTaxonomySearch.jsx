import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { publicApi } from "@/lib/api";
import { contractTypeOptions, uniqByCode } from "@/components/taxonomy";
import UnspscPicker from "@/components/UnspscPicker";

const arr = (r) => (Array.isArray(r) ? r : []);

// Homepage hero search built on the primary procurement taxonomy
// (Sector → Contract type → Category) + full country master + free text.
// All controls are optional and combine as AND filters in any order, so a
// supplier can start from Sector or Contract type or Category — "both ways".
// Submitting deep-links to /tenders/all which restores + applies the same
// query params.
export const HeroTaxonomySearch = () => {
  const navigate = useNavigate();
  const [sectors, setSectors] = useState([]);
  const [contractTypes, setContractTypes] = useState([]);
  const [countries, setCountries] = useState([]);
  const [kw, setKw] = useState("");
  const [sector, setSector] = useState("");
  const [contract, setContract] = useState("");
  const [category, setCategory] = useState("");
  const [country, setCountry] = useState("");

  useEffect(() => {
    publicApi.listSectorsPublic().then((r) => setSectors(arr(r))).catch(() => setSectors([]));
    publicApi.listContractTypesPublic().then((r) => setContractTypes(arr(r))).catch(() => setContractTypes([]));
    publicApi.countries().then((r) => setCountries(arr(r))).catch(() => setCountries([]));
  }, []);

  const submit = (e) => {
    e?.preventDefault?.();
    const p = new URLSearchParams();
    if (kw.trim()) p.set("q", kw.trim());
    if (sector) p.set("sector", sector);
    if (contract) p.set("contract", contract);
    if (category) p.set("category", category);
    if (country) p.set("country", country);
    navigate(`/tenders/all${p.toString() ? `?${p}` : ""}`);
  };

  const sel = { height: "52px" };
  return (
    <form
      className="pmc-hero__search"
      onSubmit={submit}
      data-testid="home-hero-search"
      data-nav-wired="1"
      style={{ flexWrap: "wrap", gap: "10px" }}
    >
      <label
        className="pmc-search"
        style={{ flex: "1 1 240px", height: "52px", background: "var(--surface)", borderColor: "var(--surface)" }}
      >
        <svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg>
        <input
          value={kw}
          onChange={(e) => setKw(e.target.value)}
          placeholder="Search by keyword, buyer or reference no."
          style={{ color: "var(--ink)" }}
          data-testid="home-hero-keyword"
        />
      </label>
      <select
        className="pmc-input"
        style={{ ...sel, flex: "1 1 160px" }}
        aria-label="Sector"
        value={sector}
        onChange={(e) => setSector(e.target.value)}
        data-testid="home-hero-sector"
      >
        <option value="">All sectors</option>
        {uniqByCode(sectors).map((s) => <option key={s.code} value={s.code}>{s.name}</option>)}
      </select>
      <select
        className="pmc-input"
        style={{ ...sel, flex: "1 1 180px" }}
        aria-label="Contract type"
        value={contract}
        onChange={(e) => setContract(e.target.value)}
        data-testid="home-hero-contract"
      >
        <option value="">All contract types</option>
        {contractTypeOptions(contractTypes)}
      </select>
      <div style={{ flex: "1 1 220px" }} data-testid="home-hero-category">
        <UnspscPicker testidPrefix="home-hero-category-unspsc" value={category ? " " : ""} title={category} hideValue
          inputClassName="pmc-input flex-1" placeholder="Category (e.g. solar, wind)"
          onChange={(r) => setCategory(r.title)} />
      </div>
      <select
        className="pmc-input"
        style={{ ...sel, flex: "1 1 150px" }}
        aria-label="Country"
        value={country}
        onChange={(e) => setCountry(e.target.value)}
        data-testid="home-hero-country"
      >
        <option value="">All countries</option>
        {uniqByCode(countries).map((c) => <option key={c.code} value={c.code}>{c.name}</option>)}
      </select>
      <button
        type="submit"
        className="pmc-btn pmc-btn--brass pmc-btn--lg"
        style={{ height: "52px", flex: "0 0 auto" }}
        data-testid="home-hero-find"
      >
        Find tenders
      </button>
    </form>
  );
};
