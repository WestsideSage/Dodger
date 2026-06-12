// V22 Phase 2: one money formatter for every surface. Amounts are integer
// THOUSANDS end to end (mirrors economy.format_k on the backend).
export function formatK(amountK: number): string {
  const sign = amountK < 0 ? '-' : '';
  const value = Math.abs(Math.round(amountK));
  if (value >= 1000) {
    const millions = (value / 1000).toFixed(2).replace(/\.?0+$/, '');
    return `${sign}$${millions}M`;
  }
  return `${sign}$${value}k`;
}

export function formatKSigned(amountK: number): string {
  return amountK > 0 ? `+${formatK(amountK)}` : formatK(amountK);
}
