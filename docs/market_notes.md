# Australian Data Centre Market Notes (verified 15 Sep 2026)

## (a) National capacity estimates
| Metric | Estimate | Source |
|---|---|---|
| Operational IT load, end-2025 | ~1.4 GW (Sydney ~0.8 GW, Melbourne ~0.4 GW); 162 operational facilities | Data Centres Australia / DC Byte, *Australian Data Centre Forecast Report* Issue 1, Apr 2026 (datacentres.org.au) |
| Operational IT load, FY25 | ~1.5 GW, 162 DCs, ~2% of grid-supplied electricity | AEMO Q1-2026 QED citing Dept of Industry, via certifiedstrategic.com; CommBank (Aug 2026) |
| Sydney operational, H1 2026 | 917 MW (+17% y/y); Sydney to pass 1 GW by end-2026 | Cushman & Wakefield APAC DC Update H1 2026 (Aug 2026) |
| Sydney pipeline, H1 2026 | 2,134 MW (planned 2,018 MW, +83%) | Cushman & Wakefield H1 2026 |
| Grid-connection pipeline (>5 MW projects) | 5.4 GW across 11 projects: 4.1 GW application, 1.3 GW implementation; NSW ~60%, VIC ~40% | AEMO Quarterly Energy Dynamics Q1 2026 (Apr 2026) |
| Total announced pipeline, 31 Mar 2026 | 21.6 GW: 16.8 GW early-stage, 3.1 GW committed, 0.2 GW under construction (Sydney 11.4 GW, Melbourne 9 GW) | DC Byte / Data Centres Australia, Apr 2026 |
| "Realistic" pipeline | ~6 GW, ~A$150bn central case to 2030 (A$220bn if all built) | CommBank economics, Aug 2026 |
| 2030 forecast operational | 3.2 GW national (Sydney 2.0 GW, Melbourne 1.1 GW) | DC Byte / Data Centres Australia |
| Supply gap | 1.5 GW combined Sydney+Melbourne shortfall by 2028 | CBRE, cited by Cushman & Wakefield 2026 Global Market Comparison |

Working assumption for the dashboard: **~1.4-1.5 GW operational (2025/26), ~1.0 GW under construction/committed (DC Byte committed 3.1 GW is upper bound), ~5-6 GW credible pipeline, 21.6 GW headline announcements.**

## (b) Source for each operator capacity figure
- **AirTrunk**: 1.2 GW+ across SYD1/2/3, MEL1, MEL2 = operating *plus* planned (AirTrunk MEL2 release, Dec 2025) + 1.2 GW Kemps Creek proposal (ACS/IA, Apr 2026). Operating split not disclosed -> operational null; pipeline 2,400 = total AU platform incl. operating.
- **NEXTDC**: built 288 MW, contracted 740 MW, under construction 537 MW (FY26 result, 27 Aug 2026); planned 1,815 MW incl. KL1/TK1/AK1 (1H26 pres.). Facility count 17 is approximate (company reports "25+" incl. developments).
- **CDC**: operating leasable 550 MW, under construction 810 MW, contracted >1 GW, 3.9 GW pipeline to FY40 (Infratil 30 Jun 2026 valuation via Sharecafe). Note conflicting press figures: DCD 302 MW operational (May 2026), Mingtiandi 671 MW. Figures include NZ (Auckland).
- **DigiCo**: group installed 76 MW / planned 232-238 MW (FY25); Australian contracted 41 MW target Jun-26; SYD1 expansion 88 MW (1H/FY26). Australian operational split not disclosed.
- **Macquarie Data Centres**: IC3 Super West 47 MW phase (W.Media), campus ~200 MW (techpartner.news, Aug 2026). Existing IC1/2/3E/IC4/IC5 MW not disclosed.
- **STACK**: MEL01 2x36 MW (datacentermap; MEL01A launched 2022 - operational 36 is an estimate), MEL02 252 MW (stackinfra.com); Canberra/Perth MW not public.
- **Digital Realty**: ~50 MW across 5 sites per 2020 DCD; SYD10 6 MW, SYD11 19 MW, SYD13 12 MW planned.
- **GreenSquareDC**: Sydney 4 MW -> ~110 MW (DCD Jan 2026); Perth 120 MW withdrawn (May 2026).
- **Firmus**: 1.6 GW by 2028 planned; first 150 MW mid-2026 (firmus.co) - not confirmed operational, so operational null.
- **Goodman**: Project Atlas 500 MW + 90 MW Sydney filing; power bank 6.4 GW is global. **Stockland**: MPark >100 MW + 168 MW + 250 MW Laverton North. **Centuria**: 12 + 2.5 MW operating (+Malaga, MW n/a), 250 MW pipeline (DCD Aug 2026).
- **Telstra InfraCo**: 3 DCs, 44.5 MW target IT (currently 10 MW feeds) - operational null; Minchinbury 62 MW. **Fujitsu/Next Capital**: 25 MW operational, 100 MW potential (DCD Jul 2026). **Microsoft**: Kemps Creek 190 MW per AEMO list.
- **Not public (null)**: Equinix AU MW (18 IBX, 68,000 sqm), AWS, Google, Oracle, DCI, Vocus, Interactive, Leading Edge, Edge Centres, Polaris, Infratil/HMC/Blackstone/ISPT (investors).

## (c) Caveats
1. **IT load vs facility/grid power**: AEMO and planning documents quote grid connection (MVA/MW facility power); operators quote IT load. Facility power is typically 1.2-1.5x IT load. Kemps Creek "1.2 GW" and DigiCo "120 MVA" are facility/grid figures.
2. **Contracted vs built**: NEXTDC's 740 MW and CDC's >1 GW are *contracted*; built capacity is 288 MW and 550 MW respectively. Revenue lags contracting by 2-4 years.
3. **Planned vs credible**: DC Byte's 21.6 GW pipeline is 78% early-stage; AEMO's 5.4 GW covers only projects that have lodged connection applications. Community/EPA pushback (AirTrunk Kemps Creek, GreenSquareDC Perth) and NSW renewable-PPA conditions (Goodman Atlas) are live execution risks.
4. **Hyperscaler double counting**: AWS/Microsoft/Google/Oracle capacity is largely leased inside AirTrunk, NEXTDC, CDC, Equinix halls; do not add hyperscaler MW to operator MW.
5. **Group vs Australia**: NEXTDC planned capacity and CDC operating figures include Malaysia/Japan/NZ; DigiCo includes US assets; Goodman power bank is global.
6. **Investor entries** (Infratil, HMC Capital, Blackstone, ISPT) are included for listed/PE exposure mapping; their MW fields are intentionally null. KKR, Macquarie Asset Management (owner of Vocus; sold AirTrunk 2024), IFM/GIP/BlackRock AIP and DigitalBridge appear only as reported bidders for STACK APAC (US$25bn+). AustralianSuper's data centre exposure is offshore (DataBank US$1.5bn, Vantage EMEA) - no Australian DC assets.
7. Web-search budget was exhausted late in the run; Dexus, GPT, Mirvac, Charter Hall and Hickory yielded no verifiable 2025-26 Australian DC commitments and were omitted rather than guessed.
