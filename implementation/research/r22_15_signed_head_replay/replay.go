package replay

import (
 "context"
 "encoding/hex"
 "net/http"
 "strings"
 "time"

 "sigsum.org/sigsum-go/pkg/client"
 "sigsum.org/sigsum-go/pkg/crypto"
 "sigsum.org/sigsum-go/pkg/policy"
 "sigsum.org/sigsum-go/pkg/types"
)

const policyText = `log 4644af2abd40f4895a003bca350f9d5912ab301a49c77f13e5b6d905c20a5fe6 https://test.sigsum.org/barreleye
witness poc.sigsum.org/nisse 1c25f8a44c635457e2e391d1efbca7d4c2951a0aef06225a881e46b98962ac6c
witness rgdd.se/poc-witness 28c92a5a3a054d317c86fc2eeb6a7ab2054d6217100d0be67ded5b74323c5806
witness witness1.smartit.nu/witness1 f4855a0f46e8a3e23bb40faf260ee57ab8a18249fa402f2ca2d28a60e1a3130e
group quorum-rule 2 poc.sigsum.org/nisse rgdd.se/poc-witness witness1.smartit.nu/witness1
quorum quorum-rule
`
const logKeyHash = "4e89cc51651f0d95f3c6127c15e1a42e3ddf7046c5b17b752689c402e773bb4d"

// Research harness only: endpoint/client are injected by the test, not a production interface.
func readHead(url string, hc *http.Client) (types.TreeHead, string) {
 var zero types.TreeHead
 p, err := policy.ParseConfig(strings.NewReader(policyText))
 if err != nil { return zero,"HOLD_POLICY" }
 raw, err := hex.DecodeString(logKeyHash)
 if err != nil || len(raw)!=32 { return zero,"HOLD_POLICY" }
 var kh crypto.Hash
 copy(kh[:],raw)
 ctx,cancel := context.WithTimeout(context.Background(),5*time.Second)
 defer cancel()
 cli := client.New(client.Config{URL:url,HTTPClient:hc})
 cth, err := cli.GetTreeHead(ctx)
 if err != nil { return zero,"HOLD_RESPONSE_UNAVAILABLE_OR_INVALID" }
 if err = p.VerifyCosignedTreeHead(&kh,&cth); err != nil { return zero,"HOLD_UNAUTHENTICATED_HEAD" }
 return cth.TreeHead,"AUTHENTIC_HEAD"
}

// Both values must be authenticated by the caller. Floor custody is outside this harness.
// No returned value authorizes use, trust, or a floor update.
func compare(head types.TreeHead, floor *types.TreeHead) string {
 if floor == nil { return "HOLD_FRESHNESS_UNKNOWN" }
 if head.Size < floor.Size { return "HOLD_HEAD_ROLLBACK" }
 if head.Size == floor.Size {
  if head.RootHash != floor.RootHash { return "HOLD_SAME_SIZE_CONFLICT" }
  return "MATCH_FLOOR_FRESHNESS_UNKNOWN"
 }
 return "HOLD_ADVANCE_REQUIRES_CONSISTENCY"
}

func inspect(url string,hc *http.Client,floor *types.TreeHead) string {
 h,s:=readHead(url,hc)
 if s!="AUTHENTIC_HEAD" { return s }
 return compare(h,floor)
}
