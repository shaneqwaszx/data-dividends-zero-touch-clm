import type { GoldTierRequestPreviewData } from "../types";

function label(value: string): string {
  return value.replaceAll("_", " ");
}

export default function GoldTierRequestPreview({ preview }: {
  preview: GoldTierRequestPreviewData;
}) {
  return (
    <article className="submission-plan" aria-label="GoldTier request preview">
      <div>
        <p className="section-label">Case-scoped request preview</p>
        <h3>{preview.dispatch_ready ? "Dispatch ready" : "Dispatch blocked"} · policy v{preview.policy_version}</h3>
        <p className="control-help">Bounded target fields only. Transport credentials and raw provider responses are excluded.</p>
      </div>
      {preview.operations.map((operation) => (
        <section key={operation.operation}>
          <h4>{operation.operation} · {label(operation.validation)}</h4>
          <dl>
            {operation.fields.map((field) => (
              <div key={field.target_field}>
                <dt>{field.target_field}</dt>
                <dd>
                  {field.missing ? "Missing" : field.value}
                  {" · "}{label(field.provenance)} · {label(field.authority)}
                </dd>
              </div>
            ))}
          </dl>
        </section>
      ))}
    </article>
  );
}
