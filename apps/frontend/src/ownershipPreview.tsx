// TEMPORARY local preview page; renders the dev-only ownership mock. Delete after review.
import { createRoot } from "react-dom/client";
import OwnershipPreviewMock from "./dev/ownershipPreviewMock";
import "./styles.css";
import "./design-system.css";

createRoot(document.getElementById("root")!).render(<main className="ds-root ds-shell" style={{ padding: 24, maxWidth: 1280, margin: "0 auto" }}>
  <OwnershipPreviewMock />
</main>);
