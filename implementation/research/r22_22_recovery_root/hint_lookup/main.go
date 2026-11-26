// R22.22D: untrusted leaf hints, direct authenticated inclusion; no global latest.
package main
import (
 "context"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "fmt"
 "io"
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


const start uint64=281668
const floorSize uint64=282772
const firstRoot="628a11eff388e4d381e43a62effaa07362ef0aaf8d43ad9e09289630a4c05836"
const retainedRoot="81b7ff78f817bf8460b2487d3ab3a9cfd7ba217ca17b1745e57492a0ed3d35e9"
const firstChecksum="46aae12df174dd36537e66612a9c51cd9c8c114569ed89d2093c7da47597c3b4"
const signer="0f677217484fc668497b5f79c4fc2b394cc274b6482960bdf3653af1af3d89ee"

func hash(s string) crypto.Hash { b,e:=hex.DecodeString(s);if e!=nil||len(b)!=32 {panic("bad fixed hash")};var h crypto.Hash;copy(h[:],b);return h }
func require(e error){if e!=nil {log.Fatal("HOLD: ",e)}}
type fetchProof func(uint64,uint64)(types.ConsistencyProof,error)
func checkFloor(old,current types.TreeHead,fetch fetchProof)error{
 if current.Size<old.Size{return fmt.Errorf("stale relative to retained floor")}
 if current.Size==old.Size {if old.RootHash!=current.RootHash{return fmt.Errorf("same-size conflict")};return nil}
 pr,e:=fetch(old.Size,current.Size);if e!=nil{return e}
 return pr.Verify(&old,&current)
}

type hint struct { Message string `json:"message_hex"`; Signature string `json:"signature"`; KeyHash string `json:"key_hash"` }
func leafFromHint(h hint,pub crypto.PublicKey)(types.Leaf,error){
 var leaf types.Leaf
 m,e:=hex.DecodeString(h.Message);if e!=nil||len(m)!=65||m[64]!=10{return leaf,fmt.Errorf("message format")}
 if _,e=hex.DecodeString(string(m[:64]));e!=nil||string(m[:64])!=strings.ToLower(string(m[:64])){return leaf,fmt.Errorf("event id format")}
 s,e:=hex.DecodeString(h.Signature);if e!=nil||len(s)!=64{return leaf,fmt.Errorf("signature format")}
 k,e:=hex.DecodeString(h.KeyHash);if e!=nil||len(k)!=32{return leaf,fmt.Errorf("key format")}
 first:=sha256.Sum256(m);leaf.Checksum=crypto.Hash(sha256.Sum256(first[:]));copy(leaf.Signature[:],s);copy(leaf.KeyHash[:],k)
 if !leaf.Verify(&pub){return leaf,fmt.Errorf("invalid pinned signer")}
 return leaf,nil
}
type lookup func(crypto.Hash)(types.InclusionProof,error)
func locate(h hint,pub crypto.PublicKey,head types.TreeHead,get lookup)(match,error){
 leaf,e:=leafFromHint(h,pub);if e!=nil{return match{},e}
 digest:=leaf.ToHash();pr,e:=get(digest);if e!=nil{return match{},e}
 if e=pr.Verify(&digest,&head);e!=nil{return match{},e}
 if pr.LeafIndex<start||pr.LeafIndex>=head.Size{return match{},fmt.Errorf("index outside scope")}
 return match{pr.LeafIndex,hex.EncodeToString(leaf.Checksum[:])},nil
}
func main(){
 if len(os.Args)!=1{log.Fatal("HOLD: no caller endpoint")}
 raw,e:=os.ReadFile("bootstrap.json");require(e);if len(raw)>4096{log.Fatal("HOLD: bootstrap oversize")}
 var b bootstrap;d:=json.NewDecoder(strings.NewReader(string(raw)));d.DisallowUnknownFields();require(d.Decode(&b))
 var extra any;if d.Decode(&extra)!=io.EOF{log.Fatal("HOLD: trailing bootstrap")}
 if b!=(bootstrap{Start:start,Size:start+1,Root:firstRoot,Public:signer,First:firstChecksum}){log.Fatal("HOLD: bootstrap pin mismatch")}
 raw,e=os.ReadFile("hints.json");require(e);if len(raw)>16384{log.Fatal("HOLD: hints oversize")}
 var hs []hint;d=json.NewDecoder(strings.NewReader(string(raw)));d.DisallowUnknownFields();require(d.Decode(&hs));if d.Decode(&extra)!=io.EOF||len(hs)>16{log.Fatal("HOLD: invalid hint list")}
 p,e:=policy.ParseConfig(strings.NewReader(policyText));require(e)
 pk,e:=hex.DecodeString(signer);require(e);var pub crypto.PublicKey;copy(pub[:],pk)
 kh:=hash(logKeyHash)
 cli:=client.New(client.Config{URL:logURL,HTTPClient:&http.Client{Timeout:12*time.Second,CheckRedirect:func(*http.Request,[]*http.Request)error{return fmt.Errorf("redirect denied")}}})
 ctx,cancel:=context.WithTimeout(context.Background(),120*time.Second);defer cancel()
 cth,e:=cli.GetTreeHead(ctx);require(e);require(p.VerifyCosignedTreeHead(&kh,&cth))
 fetch:=func(a,b uint64)(types.ConsistencyProof,error){return cli.GetConsistencyProof(ctx,requests.ConsistencyProof{OldSize:a,NewSize:b})}
 require(checkFloor(types.TreeHead{Size:start+1,RootHash:hash(firstRoot)},cth.TreeHead,fetch))
 require(checkFloor(types.TreeHead{Size:floorSize,RootHash:hash(retainedRoot)},cth.TreeHead,fetch))
 matches:=[]match{};seen:=map[match]bool{};lookups:=0;rejected:=0;replayed:=0;duplicates:=0
 get:=func(h crypto.Hash)(types.InclusionProof,error){lookups++;return cli.GetInclusionProof(ctx,requests.InclusionProof{Size:cth.Size,LeafHash:h})}
 for _,h:=range hs{
  m,e:=locate(h,pub,cth.TreeHead,get);if e!=nil{rejected++;continue}
  if m.Index==start||m.Checksum==firstChecksum{replayed++;continue}
  if seen[m]{duplicates++;continue};seen[m]=true;matches=append(matches,m)
 }
 result:="HOLD_NO_VERIFIED_HINT_COMPLETENESS_UNKNOWN";if len(matches)>0{result="HOLD_LATER_HINT_INCLUSION_VERIFIED"}
 require(json.NewEncoder(os.Stdout).Encode(map[string]any{"result":result,"sampled_tree_size":cth.Size,"sampled_tree_root":hex.EncodeToString(cth.RootHash[:]),"retained_floor_consistency":"PASS","bootstrap_consistency":"PASS","matching_signed_leaves":matches,"hint_count":len(hs),"proof_requests":lookups,"get_leaves_requests":0,"rejected":rejected,"bootstrap_replays":replayed,"duplicate_hints":duplicates,"complete_sampled_suffix":false,"global_latest":"NOT_ESTABLISHED","freshness":"UNKNOWN","trust_activation":"NO_GO","production":"NO_GO","merge_authorized":false}))
}
