interface SelectionSummaryProps {
  selectedPaths: Set<string>;
  tokenEstimate: number | null;
}

export function SelectionSummary({ selectedPaths, tokenEstimate }: SelectionSummaryProps) {
  const includedCount = Array.from(selectedPaths).filter((p) => !p.startsWith("!")).length;
  const excludedCount = Array.from(selectedPaths).filter((p) => p.startsWith("!")).length;

  if (includedCount === 0) return null;

  return (
    <div className="flex items-center justify-between text-sm bg-muted p-3 rounded-md">
      <span>
        <strong>{includedCount}</strong> item{includedCount !== 1 ? "s" : ""} selected
        {excludedCount > 0 && ` (${excludedCount} excluded)`}
      </span>
      {tokenEstimate !== null && (
        <span className="text-muted-foreground">~{tokenEstimate.toLocaleString()} tokens</span>
      )}
    </div>
  );
}
