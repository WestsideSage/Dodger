// frontend/src/components/dynasty/history/BannerShelf.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { BannerShelf } from './BannerShelf';

describe('BannerShelf (#97 next-banner placeholder gated on isSelf)', () => {
  it('shows the "Next banner" open slot only when showNextPlaceholder', () => {
    const { rerender } = render(<BannerShelf banners={[]} showNextPlaceholder />);
    expect(screen.getByText('Next banner')).toBeInTheDocument();
    rerender(<BannerShelf banners={[]} showNextPlaceholder={false} />);
    expect(screen.queryByText('Next banner')).not.toBeInTheDocument();
    expect(screen.getByText('No Banners Yet')).toBeInTheDocument();
  });
});
