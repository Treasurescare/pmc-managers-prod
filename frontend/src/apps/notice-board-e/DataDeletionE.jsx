import { Link } from "react-router-dom";

const P = ({ children }) => <p style={{ margin: "0 0 14px", fontSize: "16px", lineHeight: "27px", color: "var(--ink-muted, #33463E)" }}>{children}</p>;
const H = ({ children }) => <h2 style={{ fontSize: "22px", margin: "28px 0 8px" }}>{children}</h2>;

export default function DataDeletionE() {
  return (
    <div style={{ background: "#F4EFE4", minHeight: "100vh" }} data-testid="data-deletion-page">
      <div style={{ maxWidth: 760, margin: "0 auto", padding: "56px 24px 72px", fontFamily: "inherit" }}>
        <Link to="/" style={{ fontSize: 13 }} data-testid="data-deletion-home">← PMC Managers</Link>
        <div className="pmc-eyebrow" style={{ marginTop: 24 }}>Legal</div>
        <h1 className="pmc-display" style={{ fontSize: "44px", lineHeight: "50px", margin: "10px 0 16px" }}>Data deletion instructions</h1>
        <P>This page explains how to delete the data PMC Managers holds about you, including data received through Facebook, LinkedIn or Google sign-in and WhatsApp messages.</P>
        <H>1. Correct your details yourself</H>
        <P>Sign in and open <b>Account &amp; security</b> to view and correct your details. To delete your data, follow step 2.</P>
        <H>2. Ask us to delete it</H>
        <P>Email <a href="mailto:adminsupport@pmcmanagers.com" data-testid="data-deletion-email">adminsupport@pmcmanagers.com</a> from the address on your account with the subject "Delete my data". Tell us your company name and, for WhatsApp, the mobile number you messaged from. We confirm by email once it's done.</P>
        <H>3. WhatsApp</H>
        <P>To stop WhatsApp messages, reply <b>STOP</b> or switch off WhatsApp alerts in your account. Ask us as above to delete your WhatsApp message history.</P>
        <H>4. Facebook, LinkedIn or Google sign-in</H>
        <P>You can also remove PMC Managers from your Facebook, LinkedIn or Google account's connected apps settings. This stops further access; ask us as above to delete what we already hold.</P>
        <H>5. What we must keep</H>
        <P>Records the law or an open tender or contract requires (for example submitted bids, payments and the audit ledger) are kept only as long as required and anonymised where possible. See our <Link to="/privacy">Privacy notice</Link>.</P>
      </div>
    </div>
  );
}
