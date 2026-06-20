import type { KeyboardEvent, ReactNode } from 'react';
import type React from 'react';
import { useRef } from 'react';
import styles from './RadioGroup.module.css';

export type RadioGroupOption<T extends string> = {
  value: T;
  label: string;
  children?: ReactNode;
  disabled?: boolean;
  'data-testid'?: string;
};

export function RadioGroup<T extends string>({
  value,
  onChange,
  options,
  label,
  labelledBy,
  orientation = 'vertical',
  className,
  style,
  renderOption,
}: {
  value: T;
  onChange: (next: T) => void;
  options: ReadonlyArray<RadioGroupOption<T>>;
  label?: string;
  labelledBy?: string;
  orientation?: 'vertical' | 'horizontal';
  className?: string;
  style?: React.CSSProperties;
  renderOption: (args: {
    option: RadioGroupOption<T>;
    selected: boolean;
    radioProps: {
      role: 'radio';
      'aria-checked': boolean;
      tabIndex: number;
      disabled?: boolean;
      onClick: () => void;
      'data-testid'?: string;
    };
  }) => ReactNode;
}) {
  const groupRef = useRef<HTMLDivElement>(null);
  const selectedIndex = options.findIndex((o) => o.value === value);
  const tabbableIndex = selectedIndex >= 0 ? selectedIndex : 0;

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const count = options.length;
    if (count === 0) return;
    const forwardKeys =
      orientation === 'horizontal' ? ['ArrowRight', 'ArrowDown'] : ['ArrowDown', 'ArrowRight'];
    const backwardKeys =
      orientation === 'horizontal' ? ['ArrowLeft', 'ArrowUp'] : ['ArrowUp', 'ArrowLeft'];
    const current = selectedIndex >= 0 ? selectedIndex : 0;
    let nextIndex: number | null = null;
    if (forwardKeys.includes(event.key)) nextIndex = (current + 1) % count;
    else if (backwardKeys.includes(event.key)) nextIndex = (current - 1 + count) % count;
    else if (event.key === 'Home') nextIndex = 0;
    else if (event.key === 'End') nextIndex = count - 1;
    if (nextIndex === null) return;
    const option = options[nextIndex];
    if (!option || option.disabled) return;
    event.preventDefault();
    onChange(option.value);
    const radios = groupRef.current?.querySelectorAll<HTMLElement>('[role="radio"]');
    radios?.[nextIndex]?.focus();
  };

  return (
    <div
      ref={groupRef}
      role="radiogroup"
      aria-label={labelledBy ? undefined : label}
      aria-labelledby={labelledBy}
      className={`${styles.group} ${className ?? ''}`.trim()}
      style={style}
      onKeyDown={handleKeyDown}
    >
      {options.map((option, index) => {
        const selected = option.value === value;
        return (
          <div key={option.value} style={{ display: 'contents' }}>
            {renderOption({
              option,
              selected,
              radioProps: {
                role: 'radio',
                'aria-checked': selected,
                tabIndex: index === tabbableIndex ? 0 : -1,
                disabled: option.disabled,
                onClick: () => { if (!option.disabled) onChange(option.value); },
                'data-testid': option['data-testid'],
              },
            })}
          </div>
        );
      })}
    </div>
  );
}
