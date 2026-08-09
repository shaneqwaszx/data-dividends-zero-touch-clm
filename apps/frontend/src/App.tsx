const foundationItems = [
  "FastAPI health service",
  "React and TypeScript shell",
  "Mock-first integration boundary",
  "Human review retained for exceptions",
];

export default function App() {
  return (
    <main className="page-shell">
      <section className="status-card" aria-labelledby="page-title">
        <p className="eyebrow">Data Dividends · Phase 00</p>
        <div className="status-row">
          <span className="status-dot" aria-hidden="true" />
          Foundation ready
        </div>
        <h1 id="page-title">Zero-Touch Client Onboarding</h1>
        <p className="summary">
          A safe, mock-first foundation for the Singapore ACRA to GoldTier proof of concept.
        </p>
        <ul>
          {foundationItems.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        <p className="scope-note">
          Business workflow and external integrations are intentionally not active in this phase.
        </p>
      </section>
    </main>
  );
}
