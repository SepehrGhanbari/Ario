# W27 candidate discovery — PUBLIC LIST ONLY / NO OPERATOR VETTING

**2026-11-18. RESEARCH_ONLY / HOLD / NO_CONTACT / NO_ENROLLMENT / NO_INDEPENDENCE_CLAIM**

This is a read-only transcription of the public Witness Network operator tables, NOT a cryptographic or administrative endorsement. Public listing and an about page do not prove operational independence, key custody, absence of collusion, independent high-water retention or even current endpoint availability.

Primary public witness table: https://witness-network.org/witness-tables/ . Participation: https://witness-network.org/participate/ . Status: experimental, production list unavailable.

## Candidates for future *testing-list-only* scrutiny (NOT selected)

| Publicly listed operator label | Public about URL | Test-list reported | Status |
| --- | --- | --- | --- |
| Markovian Protocol | https://witness.markovianprotocol.com/about | Yes | DISCOVERED / NOT_VERIFIED |
| TrustFabric | https://transparency.dev/witnesses/ | Yes | DISCOVERED / NOT_VERIFIED |
| Elias Rudberg | https://witness1.smartit.nu/witness1/about.txt | Yes | DISCOVERED / NOT_VERIFIED |
| IPng Networks GmbH | https://ipng.ch/s/ct/#witness | Yes | DISCOVERED / NOT_VERIFIED |
| Geomys | https://geomys.org/witness/navigli | Yes in staging table | DISCOVERED / NOT_VERIFIED |
| Mullvad VPN AB | https://witness.stagemole.eu/about | Yes in staging table | DISCOVERED / NOT_VERIFIED |

This table is **not** a recommendation or a claim these are all distinct admin operators. Different names, websites, companies or networks alone are insufficient; tests must record who can administer each keeper, its key custody, rollback resistance and third-party access to previously witnessed checkpoints. Individual entries can change; recheck current directory at decision time.

## Evidence acceptance rule (for each actual operator)

1. Record independently obtained vkey and exact cosigner name, key type, date of trusted pin and external provenance; merely parsing about-page text is claimant-sourced evidence and not sufficient.
2. Confirm with a separately authenticated source whether the entity and its administrators really differ from the log publisher and from any other quorum members. Operator naming and key possession are insufficient.
3. Determine whether the operator can keep historical high-water even if Ario, Github, the log and the founder's machines are unavailable or compromised. Investigate deletion, backup recovery, key rotation and revocation.
4. Verify exact C2SP add-checkpoint cosignature over a **dedicated nonpersonal synthetic log**, then retrieve a later cosigned checkpoint from the official monitor endpoint, compare against separately retained earlier checkpoint and test consistency.
5. Require an effective quorum of truly separate operators (not two keys owned by one administrator) if the adopted policy demands it; quorum rules cannot replace custody verification.
6. No arbitrary external POST, account creation, official signup, personal-data publication or production trust activation is authorized by this shortlist.

**Outcome: CANDIDATES_IDENTIFIED_FOR_RESEARCH, ZERO INDEPENDENT_KEEPERS_VERIFIED.**
