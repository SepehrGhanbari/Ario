# R63 external custody boundary — 2026-11-26

RESEARCH_ONLY / HOLD / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE / GENESIS NO_GO.

Direct public checkpoint reads from two operator endpoints via an external HTTP fetch service, ttl=0 (origin cache possible). Both new normalized Ed25519 notes independently verified against previously pinned log and witness keys. Old Geomys head 281668 -> new common head 282772 (1104 additional log leaves, not Ario commitments); actual 14-node Merkle consistency proof PASS. Geomys signed 2026-11-26T12:46:12Z; Markovian signed 2026-11-26T12:30:01Z. New root 81b7ff78f817bf8460b2487d3ab3a9cfd7ba217ca17b1745e57492a0ed3d35e9. These are signed times, not an independently authenticated clock or nonce-bound response. Geomys extra ML-DSA signature not checked. No new Ario publication, key, or external write-quorum deployment.

GDB Security and archive.rip returned 404 for this exact log's monitor path; no general outage conclusion. GDB follows staging list; archive.rip describes its witness as TEST only. Markovian history response exposed bounded older portion only; no claim of retrieving yesterday's historical note there. Witness Network production list is not available yet (https://witness-network.org/witness-tables/). Prior inquiry awaits moderation, no enrollment confirmed. Public C2SP log cosignatures do not constitute R63 identity-specific initialization, nonce-bound read or durable per-transition receipt. Different operator names and keys do not prove administrative independence.

## Public evidence (normalized Ed25519 notes)
Geomys:
```
sigsum.org/v1/tree/4e89cc51651f0d95f3c6127c15e1a42e3ddf7046c5b17b752689c402e773bb4d
282772
gbf/ePgXv4Rgskh9OrOpz9e6IXyhexdF5XSSoO09Nek=

— sigsum.org/v1/tree/4e89cc51651f0d95f3c6127c15e1a42e3ddf7046c5b17b752689c402e773bb4d d4YpsS+wkVr+GDhVTOz4G4oensGMFNSfE4XRBZM4/S7wzx2gThjQ0HMI34TbnlyDxNjLZ8Nl50yAMRFz4iwGFDKm2gY=
— witness.navigli.sunlight.geomys.org o+AP4gAAAABrCCoU2TLx8PW8bQ4NNyvsHhve4e9rIBwhzMMFXK/0knPGCEpAU1I6+Zj5+lUzYPRW4jABrEyAc0eHjdgjAI3dcvDpCQ==
```
Markovian:
```
sigsum.org/v1/tree/4e89cc51651f0d95f3c6127c15e1a42e3ddf7046c5b17b752689c402e773bb4d
282772
gbf/ePgXv4Rgskh9OrOpz9e6IXyhexdF5XSSoO09Nek=

— sigsum.org/v1/tree/4e89cc51651f0d95f3c6127c15e1a42e3ddf7046c5b17b752689c402e773bb4d d4YpsS+wkVr+GDhVTOz4G4oensGMFNSfE4XRBZM4/S7wzx2gThjQ0HMI34TbnlyDxNjLZ8Nl50yAMRFz4iwGFDKm2gY=
— markovianprotocol.com/witness QbiCfwAAAABrCCZJnhFxNDknvvnGH6TzcVxiA4jjKlodDwz2THqR9Zr4PCgNC85F1MdcFihG4/caGof3xJCOmM5y+APebA0rbAcdBA==
```
Consistency proof 281668 -> 282772:
```
63bb405f8ad3480e114698305baea08c5c521007c67d40d295c94bf7f7da040e
f263616045a6f8e1b4700b5cb5abd1220e30d71bbaffaf6e5c28459d16b03024
8116b0bf120adbb9481bdee6d800ffde87eafe9691e328278470b5f4e4bd1a62
f5c0a99d5d4a27d791c924c5dc7d7bbee0d0fd45f004a08dca100ce78c78d405
ed2f61372f8a72d33497e567acfd38ba894b4b63406e9994d818cf058a443f49
71d8aff2f20844cb16cdc5637eb1fdaa5cd04ecaca98915ff745ee75ed9db384
1b9e19cf4277f6ff5bf674928962cc654fc7c513aa0c0bd96490298c9a2cdc1a
9beb0547c348c7e155eb485e7654f494e73dbe9b3c8b62d57a9bb8e0880df5f6
393eb5b7154f0578bc268be18ee2d212e0d83709d4097591f5bee2e3d9c42675
124a77d338c0c63bfc5a07db1f76420f14bb0c0bc6236dc60c92a80be7491956
3ca4fc8037a26123860ed4bdf0146ad64902dd8ddefc749e3638b8deead2eca7
e4c1cd4081a1974f056149f9f6d399e7807fe53e22f45001e2fb732c4b1ab61d
9f08ed43a5f9cfda6ddc96965e7793c57a154e1624a7c239e3309efb4644dabc
ed692e645805ff21bd2e71d2cfb0ebecba7c9f75be664e981c3215f08cae5081
```

## External admission requirements
Explicit operator opt-in for exact R63 test origin/scope; distinct administrative custody; documented state loss/key retirement policy; atomic state-before-response; authenticated fresh read or HOLD; permitted controlled reset/restore test; independently protected durable monotonic state; 3-of-4 finalization certificate bound to exact proposal. No common administrator capable of rolling back a quorum under the model's assumptions. No candidate admitted yet. HOLD_EXTERNAL_CUSTODY_NOT_ESTABLISHED.

Owner package Ario_R63_External_Custody_20261126.zip SHA256 c019940f641f91424db79b4c005720bfeacc623955a6de2316c12d4a9d3e49d4; CRC and manifest verified; exact notes, proof and offline verifier included. Package itself not committed. No merge.
