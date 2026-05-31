// Fake season data for the Dodger UI kit. All names invented.
window.DodgerData = {
  program: {
    name: "Westside Solstice",
    seasonYear: 2026,
    week: 4,
    record: "3-1-0",
    objective: "Establish a top-4 finish and target a recruiting Tier B class."
  },

  intents: ["Win Now", "Develop Youth", "Audition Bench", "Catch-Heavy Attrition", "Power-Arm Aggro"],
  selectedIntent: "Win Now",

  nextMatch: {
    opponent: "Northwood Cyphers",
    opponentRecord: "1-3-0",
    framing: "Your catch-heavy attrition style counters their Power-Arm Aggro -- if your catchers survive the opening volley.",
    week: 4,
    home: true,
    keyMatchup: "Mika Thorn (CAT 91) vs Theo Park (POW 87)",
    lastMeeting: "Lost 4-6 in Season 2025, Week 11."
  },

  scoutReport: {
    homeStarter: "Solstice opens with sniper control. Two starters fatigued.",
    awayStarter: "Cyphers ride Theo Park's arm + Reed's clutch catching.",
    risk: "Wet warm-up. Stamina costs ~3% higher this week."
  },

  departmentOrders: [
    { dept: "Tactics", title: "Sync throws on volley 2", body: "Coach pushes two-thrower combos on the second volley to crack their backline." },
    { dept: "Conditioning", title: "Rotate three starters", body: "Limit ironwall workload; Mika, Quinn, Avery into rotation slots if score swings 2+." },
    { dept: "Recruiting", title: "Visit Avery Helix", body: "Recruiting credibility climbs with a home-week visit. 1 slot remaining." },
    { dept: "Scouting", title: "Verify Theo Park decision", body: "Last scouting tier: KNOWN. Push to VERIFIED before next meeting." },
  ],

  readiness: {
    label: "Ready to Simulate",
    note: "Lineup confirmed, intent locked, no blocking warnings."
  },

  checklist: [
    { state: "ready", label: "Ready", title: "Lineup confirmed", body: "11 starters locked. Catchers anchored on the back line." },
    { state: "ready", label: "Ready", title: "Intent set", body: "Win Now -- pushes risk-tolerance to 0.7, sync-throws to 0.65." },
    { state: "pending", label: "Pending", title: "Visit Avery Helix", body: "1 visit slot remaining. Strong fit, home week." },
    { state: "optional", label: "Optional", title: "Pre-match scouting verification", body: "Theo Park is KNOWN -- one push to VERIFIED is available." },
  ],

  roster: [
    { id: "p1", name: "Mika Thorn", age: 31, archetype: "Balanced", role: "Starter", overall: 79, potential: "High", confidence: 4, ratings: { acc: 76, pow: 63, dod: 60, cat: 91, sta: 72, iq: 71 }, isStarter: true },
    { id: "p2", name: "Quinn Novak", age: 24, archetype: "Power", role: "Starter", overall: 74, potential: "Elite", confidence: 3, ratings: { acc: 82, pow: 88, dod: 55, cat: 41, sta: 78, iq: 60 }, isStarter: true },
    { id: "p3", name: "Ash Zane", age: 27, archetype: "Tactical", role: "Starter", overall: 72, potential: "High", confidence: 4, ratings: { acc: 64, pow: 50, dod: 84, cat: 81, sta: 75, iq: 88 }, isStarter: true },
    { id: "p4", name: "Elio Penn", age: 22, archetype: "Power", role: "Starter", overall: 71, potential: "High", confidence: 2, ratings: { acc: 79, pow: 83, dod: 52, cat: 48, sta: 80, iq: 58 }, isStarter: true },
    { id: "p5", name: "Marlon Reed", age: 29, archetype: "Tactical", role: "Starter", overall: 75, potential: "Solid", confidence: 4, ratings: { acc: 71, pow: 60, dod: 76, cat: 87, sta: 71, iq: 84 }, isStarter: true },
    { id: "p6", name: "Theo Park", age: 26, archetype: "Power", role: "Rotation", overall: 70, potential: "Solid", confidence: 3, ratings: { acc: 82, pow: 87, dod: 49, cat: 38, sta: 76, iq: 56 }, isStarter: false },
    { id: "p7", name: "June Halsey", age: 19, archetype: "Tactical", role: "Rotation", overall: 64, potential: "Elite", confidence: 1, ratings: { acc: 58, pow: 44, dod: 79, cat: 72, sta: 81, iq: 76 }, isStarter: false },
    { id: "p8", name: "Sky Larsen", age: 23, archetype: "Balanced", role: "Rotation", overall: 67, potential: "Solid", confidence: 3, ratings: { acc: 70, pow: 65, dod: 64, cat: 65, sta: 74, iq: 62 }, isStarter: false },
    { id: "p9", name: "Cass Reyes", age: 33, archetype: "Tactical", role: "Bench", overall: 62, potential: "Limited", confidence: 4, ratings: { acc: 58, pow: 48, dod: 70, cat: 73, sta: 58, iq: 75 }, isStarter: false },
    { id: "p10", name: "Bram Holloway", age: 21, archetype: "Power", role: "Rotation", overall: 66, potential: "High", confidence: 2, ratings: { acc: 75, pow: 80, dod: 50, cat: 42, sta: 79, iq: 53 }, isStarter: false },
    { id: "p11", name: "Indira Mehta", age: 25, archetype: "Balanced", role: "Bench", overall: 60, potential: "Limited", confidence: 3, ratings: { acc: 62, pow: 58, dod: 60, cat: 60, sta: 65, iq: 60 }, isStarter: false },
  ],

  recruits: [
    { id: "r1", name: "Avery Helix", hometown: "Bishop", archetype: "Balanced", ovrBand: [75, 85], fitScore: 82, fitTier: "strong", evidence: "Shows interest after Solstice's catch-heavy attrition win." },
    { id: "r2", name: "Tobin Yates", hometown: "Riverton", archetype: "Power", ovrBand: [70, 80], fitScore: 64, fitTier: "neutral", evidence: "Open to visits. Prefers volume programs." },
    { id: "r3", name: "Nia Cortes", hometown: "Glen Lake", archetype: "Tactical", ovrBand: [78, 88], fitScore: 88, fitTier: "strong", evidence: "Wants a tactical role; impressed by Ash Zane's reads." },
    { id: "r4", name: "Devon Ortiz", hometown: "Pine Hills", archetype: "Balanced", ovrBand: [65, 75], fitScore: 41, fitTier: "risk", evidence: "Skeptical of our backline depth." },
    { id: "r5", name: "Sela Brooks", hometown: "Foxbridge", archetype: "Power", ovrBand: [80, 90], fitScore: 75, fitTier: "strong", evidence: "Top in district. Has visited two rival programs." },
    { id: "r6", name: "Owen Vance", hometown: "Cedar Crest", archetype: "Tactical", ovrBand: [68, 78], fitScore: 58, fitTier: "neutral", evidence: "Awaiting scouting verification." },
  ],

  credibility: {
    tier: "C",
    score: 61,
    evidence: [
      "5 command-history wins and 3 losses.",
      "0 youth-development command weeks.",
      "Club prestige score 0.",
    ],
  },

  slots: { scout: [0, 3], contact: [1, 5], visit: [0, 1] },

  staff: [
    { dept: "Head Coach", name: "Reyna Calder", rating: 72, voice: "Clipboard analyst." },
    { dept: "Recruiting", name: "Marv Booker", rating: 68, voice: "Old-school regional grinder." },
    { dept: "Scouting", name: "Yuki Tan", rating: 80, voice: "Numbers-first decision feel." },
    { dept: "Conditioning", name: "Hal Greer", rating: 65, voice: "Stamina-and-survive philosophy." },
  ],

  standings: [
    { rank: 1, club: "Foxbridge Volley", w: 4, l: 0, d: 0, pts: 12, diff: "+18", user: false },
    { rank: 2, club: "Glen Lake Tactics", w: 3, l: 1, d: 0, pts: 9, diff: "+8", user: false },
    { rank: 3, club: "Pine Hills Burn", w: 3, l: 1, d: 0, pts: 9, diff: "+5", user: false },
    { rank: 4, club: "Westside Solstice", w: 3, l: 1, d: 0, pts: 9, diff: "+4", user: true },
    { rank: 5, club: "Cedar Crest Reads", w: 2, l: 2, d: 0, pts: 6, diff: "+1", user: false },
    { rank: 6, club: "Bishop Bench", w: 2, l: 2, d: 0, pts: 6, diff: "-2", user: false },
    { rank: 7, club: "Riverton Volume", w: 2, l: 2, d: 0, pts: 6, diff: "-3", user: false },
    { rank: 8, club: "Carbon Bay Lash", w: 1, l: 3, d: 0, pts: 3, diff: "-11", user: false },
    { rank: 9, club: "Northwood Cyphers", w: 1, l: 3, d: 0, pts: 3, diff: "-12", user: false },
    { rank: 10, club: "Iron Hollow Steel", w: 0, l: 4, d: 0, pts: 0, diff: "-18", user: false },
  ],

  recentMatches: [
    { week: 3, summary: "Solstice 6-2 Bishop Bench", winner: "Solstice" },
    { week: 3, summary: "Foxbridge 8-1 Iron Hollow Steel", winner: "Foxbridge" },
    { week: 3, summary: "Glen Lake 5-3 Cedar Crest Reads", winner: "Glen Lake" },
    { week: 3, summary: "Pine Hills 7-2 Riverton Volume", winner: "Pine Hills" },
    { week: 3, summary: "Northwood Cyphers 4-4 Carbon Bay Lash", winner: "Draw" },
  ],

  // Post-sim aftermath (revealed after clicking Simulate Week)
  aftermath: {
    headline: "Solstice shut out Northwood Cyphers 8-0 in a catch-led collapse.",
    contextLine: "An 8-0 shutout that leaves no room for excuses.",
    matchCard: { home: "Westside Solstice", away: "Northwood Cyphers", homeSurv: 8, awaySurv: 0, winner: "home" },
    turningPoint: "Ash Zane reversed possession on volley 2 with a clean catch on Theo Park. Cyphers' backline never recovered.",
    evidenceLanes: [
      { title: "Possession", summary: "Solstice owned 71% of post-volley possession.", items: ["Sync throws on volleys 2, 4, 6", "Cyphers averaged 1.4s on offence per possession"] },
      { title: "Catching", summary: "Three catches reversed three Cypher attacks.", items: ["Ash Zane catch on Theo Park (volley 2)", "Marlon Reed catch on Reed (volley 5)"] },
    ],
    keyPerformers: [
      { name: "Mika Thorn", club: "Westside Solstice", line: "3 eliminations -- 1 catch -- +18 impact", score: 18 },
      { name: "Ash Zane",   club: "Westside Solstice", line: "2 eliminations -- 2 dodges -- +12 impact", score: 12 },
      { name: "Elio Penn",  club: "Westside Solstice", line: "1 elimination -- 4 sync assists -- +9 impact", score: 9 },
    ],
    growth: [
      { name: "Quinn Novak", attr: "Power", delta: 1 },
      { name: "June Halsey", attr: "Dodge", delta: 1 },
    ],
    standingsShift: [
      { club: "Westside Solstice", old: 5, current: 4 },
      { club: "Northwood Cyphers", old: 7, current: 9 },
    ],
    recruitReactions: [
      { name: "Avery Helix", delta: "+", evidence: "Saw the catch-heavy win on the report wire." },
    ]
  },

  // Replay events
  replayEvents: [
    { idx: 1, phase: "OPENING -- 00:14", type: "throw", title: "Marlon Reed opens with a sniper throw. Theo Park dodges.", details: ["Accuracy 71 vs Dodge 49 -- p_hit 0.62 -- roll 0.71 -- DODGE"] },
    { idx: 2, phase: "OPENING -- 00:42", type: "elim", title: "Mika Thorn tagged Quinn Reed.", details: ["Accuracy 76 vs Dodge 58 -- p_hit 0.68 -- roll 0.41 -- HIT"] },
    { idx: 3, phase: "VOLLEY 2 -- 01:18", type: "catch", title: "Ash Zane caught Theo Park's throw. Possession swings.", details: ["Catch 84 vs Accuracy 82 -- p_catch 0.42 -- roll 0.31 -- CATCH", "Theo Park benched on possession rule"] },
    { idx: 4, phase: "MIDGAME -- 02:04", type: "throw", title: "Elio Penn sync-throw on backline.", details: ["Sync mod +0.10 -- p_hit 0.76 -- roll 0.62 -- HIT"] },
    { idx: 5, phase: "MIDGAME -- 03:27", type: "elim", title: "Cyphers lose final backline defender.", details: ["Stamina-failure modifier active -- p_dodge 0.18 -- roll 0.55 -- HIT"] },
    { idx: 6, phase: "ENDGAME -- 04:10", type: "elim", title: "Solstice snowballs possession.", details: ["3 consecutive possessions converted"] },
    { idx: 7, phase: "ENDGAME -- 05:31", type: "final", title: "Final Out. Solstice wins 8-0.", details: ["8 survivors -- 0 survivors"] },
  ],
};
