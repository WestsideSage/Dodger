import { ActionButton } from '../ui';

export function IdentityStep({ identity, setIdentity, onNext }: { identity: any, setIdentity: (v: any) => void, onNext: () => void }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <h2>Build a Program: Identity</h2>
      <input type="text" placeholder="Save Name" value={identity.save_name} onChange={e => setIdentity({...identity, save_name: e.target.value})} style={{ padding: '0.5rem' }} />
      <input type="text" placeholder="Club Name" value={identity.club_name} onChange={e => setIdentity({...identity, club_name: e.target.value})} style={{ padding: '0.5rem' }} />
      <input type="text" placeholder="City" value={identity.city} onChange={e => setIdentity({...identity, city: e.target.value})} style={{ padding: '0.5rem' }} />
      <input type="text" placeholder="Colors (e.g., #FF0000,#000000)" value={identity.colors} onChange={e => setIdentity({...identity, colors: e.target.value})} style={{ padding: '0.5rem' }} />
      <ActionButton onClick={onNext} disabled={!identity.save_name || !identity.club_name || !identity.city}>Next: Coach Profile</ActionButton>
    </div>
  );
}
