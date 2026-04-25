type Props = {
  title?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
};

export function SectionCard({
  title,
  action,
  children,
  className = "",
}: Props) {
  return (
    <section
      className={`rounded-lg border border-neutral-800 bg-neutral-900/40 ${className}`}
    >
      {title || action ? (
        <header className="flex items-center justify-between border-b border-neutral-800 px-4 py-3">
          {title ? <h2 className="text-sm font-medium text-neutral-200">{title}</h2> : <div />}
          {action}
        </header>
      ) : null}
      <div className="p-4">{children}</div>
    </section>
  );
}
