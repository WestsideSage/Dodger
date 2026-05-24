from __future__ import annotations

from typing import Sequence
from .models import Player
from .lineup import optimize_ai_lineup

def optimize_archetype_lineup(
    roster: Sequence[Player],
    archetype: str,
    intent: str,
) -> list[str]:
    """Wraps optimize_ai_lineup to adjust the starters based on club archetype and intent.
    
    For 'Development Factory' clubs: if the week is not 'must-win' (intent is not 'Win Now'
    or 'Prepare For Playoffs'), we swap in one high-potential rookie (traits.potential >= 70,
    newcomer status) in place of a lower-potential veteran, provided the rookie's current
    conditioning/fatigue viability (conditioning_curve >= 50) allows it.
    """
    lineup_ids = list(optimize_ai_lineup(roster))
    
    if archetype == "Development Factory" and intent not in ("Win Now", "Prepare For Playoffs"):
        players_by_id = {p.id: p for p in roster}
        starters = [players_by_id[pid] for pid in lineup_ids[:6] if pid in players_by_id]
        bench = [players_by_id[pid] for pid in lineup_ids[6:] if pid in players_by_id]
        
        # Find eligible rookies on the bench
        eligible_rookies = []
        for p in bench:
            is_rookie = getattr(p, "newcomer", False)
            potential = p.traits.potential if p.traits else 50.0
            cond_curve = p.ratings.conditioning_curve if p.ratings else 50.0
            if is_rookie and potential >= 70 and cond_curve >= 50:
                eligible_rookies.append(p)
                
        if eligible_rookies:
            # Sort eligible rookies by potential, then overall skill descending
            eligible_rookies.sort(key=lambda p: (-p.traits.potential, -p.overall_skill()))
            rookie_to_promote = eligible_rookies[0]
            
            # Find a lower-potential veteran in the starters to swap with
            eligible_vets = []
            for p in starters:
                is_rookie = getattr(p, "newcomer", False)
                potential = p.traits.potential if p.traits else 50.0
                if not is_rookie and potential < rookie_to_promote.traits.potential:
                    eligible_vets.append(p)
                    
            if eligible_vets:
                # Sort veterans by potential ascending, then overall skill ascending (replace the weakest/lowest potential first)
                eligible_vets.sort(key=lambda p: (p.traits.potential, p.overall_skill()))
                vet_to_replace = eligible_vets[0]
                
                # Swap the rookie and the veteran in the lineup
                idx_vet = lineup_ids.index(vet_to_replace.id)
                idx_rookie = lineup_ids.index(rookie_to_promote.id)
                lineup_ids[idx_vet], lineup_ids[idx_rookie] = lineup_ids[idx_rookie], lineup_ids[idx_vet]
                
    return lineup_ids
