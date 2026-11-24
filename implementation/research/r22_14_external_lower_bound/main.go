// R22.14: first verified later same-key leaf is a conservative HOLD even in a partial scan. Research only.
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

const maxLeaves uint64 = 8
const logURL = "https://test.sigsum.org/barreleye"
const logKeyHash = "4e89cc51651f0d95f3c6127c15e1a42e3ddf7046c5b17b752689c402e773bb4d"
type bootstrap struct {
 Start uint64 `json:"start"`
 Size uint64 `json:"size"`
 Root string `json:"root"`
 Public string `json:"public"`
 First string `json:"first_checksum"`
}
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

func resolve(matches []match, start uint64, first string, complete bool) (int, string) {
 if len(matches)==0 || matches[0].Index!=start || matches[0].Checksum!=first { return 0,"HOLD_BOOTSTRAP_NOT_FOUND" }
 for i:=1;i<len(matches);i++ {
  if matches[i].Index<=matches[i-1].Index || matches[i].Checksum==first { return 0,"HOLD_ORDER_OR_DUPLICATE" }
 }
 if len(matches)>1 { return len(matches)-1,"HOLD_LATER_SIGNED_COMMITMENT" }
 if !complete { return 0,"HOLD_INCOMPLETE_SCAN" }
 return 0,"HOLD_NO_NEW_MATCH_FRESHNESS_UNKNOWN"
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
 if len(os.Args) != 1 { log.Fatal("HOLD: no caller-controlled endpoint") }
 file,err:=os.Open("bootstrap.json")
 require(err)
 defer file.Close()
 st,err:=file.Stat()
 require(err)
 if st.Size()>4096 { log.Fatal("HOLD: bootstrap oversize") }
 var boot bootstrap
 dec:=json.NewDecoder(file)
 dec.DisallowUnknownFields()
 require(dec.Decode(&boot))
 if boot.Size<=boot.Start || boot.Start==0 || boot.Size-boot.Start>maxLeaves { log.Fatal("HOLD: invalid bootstrap position") }
 start:=boot.Start
 _=hash(boot.First)
 p, err := policy.ParseConfig(strings.NewReader(policyText))
 require(err)
 pubBytes, err := hex.DecodeString(boot.Public)
 require(err)
 var pub crypto.PublicKey
 copy(pub[:], pubBytes)
 if len(pubBytes)!=32 { log.Fatal("HOLD: signer pin length") }
 signerHash := crypto.Hash(sha256.Sum256(pub[:]))
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
 prior := types.TreeHead{Size:boot.Size, RootHash:hash(boot.Root)}
 if cth.Size < prior.Size { log.Fatal("HOLD: stale tree head relative to supplied bootstrap") }
 if cth.Size == prior.Size {
  if cth.RootHash != prior.RootHash { log.Fatal("HOLD: same-size conflict") }
 } else {
  proof, err := cli.GetConsistencyProof(ctx, requests.ConsistencyProof{OldSize:prior.Size, NewSize:cth.Size})
  require(err)
  require(proof.Verify(&prior, &cth.TreeHead))
 }
 fmt.Printf("R22_14_COSIGNED_TREE size=%d root=%x consistency=PASS\n", cth.Size, cth.RootHash)
 end := cth.Size
 if end-start > maxLeaves { end = start+maxLeaves }
 cursor := start
 matches := []match{}
scan:
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
   if leaf.KeyHash == signerHash {
    if !leaf.Verify(&pub) { log.Fatal("HOLD: invalid matching signer leaf signature") }
    matches=append(matches,match{Index:cursor,Checksum:hex.EncodeToString(leaf.Checksum[:])})
   }
   cursor++
   if len(matches)>1 { break scan }
  }
 }
 discovered, disposition := resolve(matches,start,boot.First,cursor==cth.Size)
 result := map[string]any{
  "sampled_tree_size":cth.Size, "sampled_tree_root":hex.EncodeToString(cth.RootHash[:]),
  "scan_start":start, "scan_end_exclusive":cursor, "verified_leaf_count":cursor-start,
  "complete_sampled_suffix":cursor==cth.Size, "matching_signed_leaves":matches,
  "scan_limit":maxLeaves, "old_state_admissible":false,
  "new_opaque_signed_commitments":discovered, "disposition":disposition,
  "recovered_content":false, "verified_scope_sequence":"UNKNOWN",
  "global_latest_scope":"NOT_ESTABLISHED", "source_freshness":"NOT_ESTABLISHED",
  "independent_latest_floor":"NOT_ESTABLISHED", "history_truth":"UNKNOWN",
  "trust_activation":"NO_GO","production":"NO_GO","merge_authorized":false,
 }
 enc:=json.NewEncoder(os.Stdout)
 require(enc.Encode(result))
 // Success of discovery experiment is NOT an acceptance decision.
 if discovered!=1 || disposition!="HOLD_LATER_SIGNED_COMMITMENT" { log.Fatal("HOLD: no verified later same-key leaf found") }
}
