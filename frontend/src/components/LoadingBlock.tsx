export function LoadingBlock({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="flex items-center justify-center py-12 text-sm text-neutral-500">
      {label}
    </div>
  );
}
