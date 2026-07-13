export function OptionValueCell({ value }: { value: string }) {
  return (
    <td className="option-value-cell">
      <strong>{value}</strong>
    </td>
  );
}
