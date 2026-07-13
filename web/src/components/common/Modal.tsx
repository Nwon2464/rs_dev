import { useEffect, useRef, type ReactNode } from "react";
import { uiText, type Language } from "../../i18n";

export function Modal({
  language,
  title,
  subtitle,
  children,
  onClose,
}: {
  language: Language;
  title: string;
  subtitle: string;
  children: ReactNode;
  onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    dialog.current?.showModal();
  }, []);
  return (
    <dialog
      ref={dialog}
      className="candidate-dialog"
      onCancel={onClose}
      onClick={(event) => {
        if (event.currentTarget === event.target) onClose();
      }}
    >
      <div className="dialog-inner">
        <div className="dialog-head">
          <div>
            <h2>{title}</h2>
            <p>{subtitle}</p>
          </div>
          <button aria-label={uiText(language, "common.close")} onClick={onClose}>
            ×
          </button>
        </div>
        {children}
      </div>
    </dialog>
  );
}
