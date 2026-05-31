import { formatSeasonLabel } from './formatters';
import { EmptyState } from '../../../legibility/EmptyState';

interface BannerEntry {
  type: string;
  season: string;
  label: string;
}

export function BannerShelf({
  banners,
  showNextPlaceholder,
}: {
  banners: BannerEntry[];
  showNextPlaceholder?: boolean;
}) {
  if (banners.length === 0 && !showNextPlaceholder) {
    return <EmptyState title="No Banners Yet" body="No banners are hanging in this archive yet." />;
  }

  return (
    <div className="do-hist-banners">
      {banners.map((banner, index) => (
        <div key={`${banner.type}-${banner.season}-${index}`} className={`do-hist-banner ${banner.type === 'championship' ? 'is-title' : 'is-award'}`}>
          <span className="do-hist-banner-type">{banner.type === 'championship' ? 'Title' : 'Award'}</span>
          <strong className="do-hist-banner-label">{banner.label}</strong>
          <span className="do-hist-banner-season">{formatSeasonLabel(banner.season)}</span>
        </div>
      ))}
      {showNextPlaceholder ? (
        <div className="do-hist-banner do-hist-banner-empty">
          <span className="do-hist-banner-type">Open Slot</span>
          <strong className="do-hist-banner-label">Next banner</strong>
          <span className="do-hist-banner-season">Still to be won</span>
        </div>
      ) : null}
    </div>
  );
}
