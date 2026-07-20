export function OptionTitle({ title }: { title: string }) {
  return (
    <strong className="option-title" title={title}>
      {title}
    </strong>
  );
}
