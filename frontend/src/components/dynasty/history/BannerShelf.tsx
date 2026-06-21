import { formatSeasonLabel } from './formatters';
import { EmptyState } from '../../../legibility/EmptyState';
import styles from './BannerShelf.module.css';

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
    <div className={styles.banners}>
      {banners.map((banner, index) => (
        <div key={`${banner.type}-${banner.season}-${index}`} className={`${styles.banner} ${banner.type === 'championship' ? styles.bannerTitle : ''}`}>
          <span className={styles.bannerType}>{banner.type === 'championship' ? 'Title' : 'Award'}</span>
          <strong className={styles.bannerLabel}>{banner.label}</strong>
          <span className={styles.bannerSeason}>{formatSeasonLabel(banner.season)}</span>
        </div>
      ))}
      {showNextPlaceholder ? (
        <div className={`${styles.banner} ${styles.bannerEmpty}`}>
          <span className={styles.bannerType}>Open Slot</span>
          <strong className={styles.bannerLabel}>Next banner</strong>
          <span className={styles.bannerSeason}>Still to be won</span>
        </div>
      ) : null}
    </div>
  );
}
