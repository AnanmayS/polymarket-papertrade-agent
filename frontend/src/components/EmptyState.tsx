type Props = {
  title?: string;
  hint?: string;
};

export function EmptyState({ title = "No data", hint }: Props) {
  const cleanHint = hint
    ? hint.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim().slice(0, 240)
    : null;

  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="text-sm font-medium text-neutral-300">{title}</div>
      {cleanHint ? (
        <div className="mt-1 max-w-md text-xs text-neutral-500">{cleanHint}</div>
      ) : null}
    </div>
  );
}
