import { getTerm, type TermId } from './terms';
import styles from './TermLabel.module.css';

/**
 * Non-interactive sibling of {@link TermTip}. Use ONLY where a TermTip's
 * `<button>` would nest inside an interactive ancestor — a `role="button"`
 * standings row or a `role="checkbox"` prospect card. A button inside another
 * interactive element is an axe `nested-interactive` WCAG violation and trips
 * React's `validateDOMNesting` warning.
 *
 * The term's definition degrades from the rich popover to a native `title`
 * tooltip. That stays readable to screen readers and AI agents because it
 * lives in the DOM (unlike a CSS-only hover reveal), and the dotted underline
 * keeps the same "there is more to read here" affordance TermTip has.
 */
export function TermLabel({
  term,
  children,
  className,
}: {
  term: TermId;
  children: React.ReactNode;
  className?: string;
}) {
  const def = getTerm(term);
  return (
    <span
      className={`${styles.label}${className ? ` ${className}` : ''}`}
      title={`${def.label} — ${def.plain} ${def.why}`}
    >
      {children}
    </span>
  );
}
