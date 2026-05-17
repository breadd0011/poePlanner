export function ItemEditorWarnings({ warnings }: { warnings: string[] }) {
  if (!warnings.length) return null;

  return (
    <section className="soft-warning-panel">
      <strong>Soft warnings</strong>
      {warnings.map((warning) => (
        <p key={warning}>{warning}</p>
      ))}
    </section>
  );
}
