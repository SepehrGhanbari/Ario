// R22.9 read-only TEST-log recovery probe. No keys, writes, submission,
// production authority or claims of independently administered latest floor.
package main

import (
 "context"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "fmt"
 "log"
 "net/http"
 "os"
 "strings"
 "time"

 "sigsum.org/sigsum-go/pkg/client"
 "sigsum.org/sigsum-go/pkg/crypto"
 "sigsum.org/sigsum-go/pkg/policy"
 "sigsum.org/sigsum-go/pkg/requests"
 "sigsum.org/sigsum-go/pkg/types"
)

// Public, externally supplied research bootstrap, not recovered local state.
// The locator is a lower bound for the scan, not proof of latest.
const start uint64 = 281316
const maxLeaves uint64 = 32
const logURL = "https://test.sigsum.org/barreleye"
const logKeyHash = "4e89cc51651f0d95f3c6127c15e1a42e3ddf7046c5b17b752689c402e773bb4d"
const priorRoot = "92d02e588e5f85e1b57656093290f55079ec54241859be1c770719d0d5e98a27"
const signerPublic = "a54f4ee1b9a07a7ff07007b86026ff73def7ae2a01ae50df3e3fe792187dc0f7"
const signerHash = "7ea08d3b91d12e892d0bf23c6212108ac04d47fcbc81a87bf066379f6c43f3e3"
const oldChecksum = "079934bedf8df6172e0c9267f8f7501225fae4626f9d3280a3988af84da43c44"
const newChecksum = "f1c1e3f6745611636ac0ed94edc01c35be3079e5dbc0bca184388a0cbccd4d8c"
const policyText = `log 4644af2abd40f4895a003bca350f9d5912ab301a49c77f13e5b6d905c20a5fe6 https://test.sigsum.org/barreleye
witness poc.sigsum.org/nisse 1c25f8a44c635457e2e391d1efbca7d4c2951a0aef06225a881e46b98962ac6c
witness rgdd.se/poc-witness 28c92a5a3a054d317c86fc2eeb6a7ab2054d6217100d0be67ded5b74323c5806
witness witness1.smartit.nu/witness1 f4855a0f46e8a3e23bb40faf260ee57ab8a18249fa402f2ca2d28a60e1a3130e
group quorum-rule 2 poc.sigsum.org/nisse rgdd.se/poc-witness witness1.smartit.nu/witness1
quorum quorum-rule
`

type match struct {
 Index uint64 `json:"index"`
 Checksum string `json:"checksum"`
}

func resolve(matches []match, complete bool) (int, string) {
 // Only authenticated matching-signer entries enter this function.
 // The registry contains two possible preimages, not a claim either was logged.
 count := 0
 for _, entry := range matches {
  n := 0
  switch entry.Checksum {
  case oldChecksum: n = 2
  case newChecksum: n = 4
  default: return count, "HOLD_OPAQUE_SIGNER_ENTRY"
  }
  if n < count { return count, "HOLD_SCOPE_SEQUENCE_REGRESSION" }
  count = n
 }
 if count == 0 { return 0, "HOLD_NO_KNOWN_ENTRY" }
 if !complete { return count, "HOLD_INCOMPLETE_SCAN" }
 return count, "KNOWN_CANDIDATE_RECOVERED_IN_BOUNDED_SAMPLED_SUFFIX_ONLY"
}

func hash(s string) crypto.Hash {
 b, e := hex.DecodeString(s)
 if e != nil || len(b) != 32 { panic("bad public bootstrap hash") }
 var h crypto.Hash
 copy(h[:], b)
 return h
}
func require(err error) { if err != nil { log.Fatal("HOLD: ", err) } }

func main() {
 if len(os.Args) != 1 { log.Fatal("HOLD: no caller-controlled endpoint or locator") }
 p, err := policy.ParseConfig(strings.NewReader(policyText))
 require(err)
 pubBytes, err := hex.DecodeString(signerPublic)
 require(err)
 var pub crypto.PublicKey
 copy(pub[:], pubBytes)
 if crypto.Hash(sha256.Sum256(pub[:])) != hash(signerHash) { log.Fatal("HOLD: signer pin") }
 kh := hash(logKeyHash)
 httpClient := &http.Client{
  Timeout: 12*time.Second,
  CheckRedirect: func(*http.Request, []*http.Request) error { return fmt.Errorf("redirect denied") },
 }
 cli := client.New(client.Config{URL:logURL, HTTPClient:httpClient})
 ctx, cancel := context.WithTimeout(context.Background(), 150*time.Second)
 defer cancel()
 cth, err := cli.GetTreeHead(ctx)
 require(err)
 require(p.VerifyCosignedTreeHead(&kh, &cth))
 prior := types.TreeHead{Size:start+1, RootHash:hash(priorRoot)}
 if cth.Size < prior.Size { log.Fatal("HOLD: stale tree head relative to supplied bootstrap") }
 if cth.Size == prior.Size {
  if cth.RootHash != prior.RootHash { log.Fatal("HOLD: same-size conflict") }
 } else {
  proof, err := cli.GetConsistencyProof(ctx, requests.ConsistencyProof{OldSize:prior.Size, NewSize:cth.Size})
  require(err)
  require(proof.Verify(&prior, &cth.TreeHead))
 }
 fmt.Printf("R22_9_COSIGNED_TREE size=%d root=%x consistency=PASS\n", cth.Size, cth.RootHash)
 end := cth.Size
 if end-start > maxLeaves { end = start+maxLeaves }
 cursor := start
 matches := []match{}
 for cursor < end {
  leaves, err := cli.GetLeaves(ctx, requests.Leaves{StartIndex:cursor, EndIndex:end})
  require(err)
  if len(leaves)==0 || uint64(len(leaves))>end-cursor { log.Fatal("HOLD: short/oversized page") }
  for _, leaf := range leaves {
   h := leaf.ToHash()
   proof, err := cli.GetInclusionProof(ctx, requests.InclusionProof{Size:cth.Size, LeafHash:h})
   require(err)
   if proof.LeafIndex != cursor { log.Fatal("HOLD: leaf index mismatch") }
   require(proof.Verify(&h, &cth.TreeHead))
   if leaf.KeyHash == hash(signerHash) {
    require(leaf.Verify(map[crypto.Hash]crypto.PublicKey{hash(signerHash):pub}))
    matches=append(matches,match{Index:cursor,Checksum:hex.EncodeToString(leaf.Checksum[:])})
   }
   cursor++
  }
 }
 recovered, disposition := resolve(matches,cursor==cth.Size)
 result := map[string]any{
  "sampled_tree_size":cth.Size, "sampled_tree_root":hex.EncodeToString(cth.RootHash[:]),
  "scan_start":start, "scan_end_exclusive":cursor, "verified_leaf_count":cursor-start,
  "complete_sampled_suffix":cursor==cth.Size, "matching_signed_leaves":matches,
  "highest_known_candidate_count":recovered, "disposition":disposition,
  "global_latest_scope":"NOT_ESTABLISHED", "source_freshness":"NOT_ESTABLISHED",
  "independent_latest_floor":"NOT_ESTABLISHED", "history_truth":"UNKNOWN",
  "trust_activation":"NO_GO","production":"NO_GO","merge_authorized":false,
 }
 enc:=json.NewEncoder(os.Stdout)
 require(enc.Encode(result))
 // Test requires retrieval of the known R22.8 commitment; no implicit adoption.
 if recovered != 4 { log.Fatal("HOLD: expected known checkpoint was not recovered") }
}
