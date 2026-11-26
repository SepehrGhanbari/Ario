// Read-only historical successor consistency checker; no candidate index/digest pin.
package main
import (
 "bytes"
 "context"
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
 "sigsum.org/sigsum-go/pkg/proof"
 "sigsum.org/sigsum-go/pkg/requests"
 "sigsum.org/sigsum-go/pkg/types"
)
const logURL = "https://test.sigsum.org/barreleye"
const logKeyHash = "4e89cc51651f0d95f3c6127c15e1a42e3ddf7046c5b17b752689c402e773bb4d"
const policyText = `log 4644af2abd40f4895a003bca350f9d5912ab301a49c77f13e5b6d905c20a5fe6 https://test.sigsum.org/barreleye
witness poc.sigsum.org/nisse 1c25f8a44c635457e2e391d1efbca7d4c2951a0aef06225a881e46b98962ac6c
witness rgdd.se/poc-witness 28c92a5a3a054d317c86fc2eeb6a7ab2054d6217100d0be67ded5b74323c5806
witness witness1.smartit.nu/witness1 f4855a0f46e8a3e23bb40faf260ee57ab8a18249fa402f2ca2d28a60e1a3130e
group quorum-rule 2 poc.sigsum.org/nisse rgdd.se/poc-witness witness1.smartit.nu/witness1
quorum quorum-rule
`

func hash(s string) crypto.Hash { b,e:=hex.DecodeString(s);if e!=nil||len(b)!=32 {panic("bad fixed hash")};var h crypto.Hash;copy(h[:],b);return h }
func require(e error){if e!=nil {log.Fatal("HOLD: ",e)}}
type fetchProof func(uint64,uint64)(types.ConsistencyProof,error)
func checkFloor(old,current types.TreeHead,fetch fetchProof)error{
 if current.Size<old.Size{return fmt.Errorf("stale relative to retained floor")}
 if current.Size==old.Size {if old.RootHash!=current.RootHash{return fmt.Errorf("same-size conflict")};return nil}
 pr,e:=fetch(old.Size,current.Size);if e!=nil{return e}
 return pr.Verify(&old,&current)
}


const historicalSigner="34cd87aa0e4513878e2d9b740bfed3fe255b082dd739b266f9c7c702b784f358"
const retainedSize uint64=282787
const retainedRoot="e8edc87b0dae1f138ba543763adbbcf625b1e6b0a43d5b2bd9fec55cbc9cf676"
func readReceipt(prefix string,p *policy.Policy,keys map[crypto.Hash]crypto.PublicKey)(proof.SigsumProof,crypto.Hash){
 raw,e:=os.ReadFile(prefix+".proof");require(e);if len(raw)>16384{log.Fatal("HOLD proof bounds")}
 msg,e:=os.ReadFile(prefix+".msg");require(e);if len(msg)!=65||msg[64]!=10{log.Fatal("HOLD message format")}
 if _,e=hex.DecodeString(string(msg[:64]));e!=nil{log.Fatal("HOLD message id")}
 var pr proof.SigsumProof;require(pr.FromASCII(bytes.NewReader(raw)))
 if pr.LogKeyHash!=hash(logKeyHash){log.Fatal("HOLD wrong log")}
 h:=crypto.HashBytes(msg);require(pr.Verify(&h,keys,p));return pr,h
}
func main(){
 if len(os.Args)!=1{log.Fatal("HOLD no caller endpoint")}
 p,e:=policy.ParseConfig(strings.NewReader(policyText));require(e)
 k,e:=hex.DecodeString(historicalSigner);require(e);var pub crypto.PublicKey;copy(pub[:],k)
 keys:=map[crypto.Hash]crypto.PublicKey{crypto.HashBytes(pub[:]):pub}
 a,_:=readReceipt("old",p,keys);b,msg:=readReceipt("new",p,keys)
 if b.Inclusion.LeafIndex<=a.Inclusion.LeafIndex||b.TreeHead.Size<a.TreeHead.Size{log.Fatal("HOLD log order")}
 cli:=client.New(client.Config{URL:logURL,HTTPClient:&http.Client{Timeout:12*time.Second,CheckRedirect:func(*http.Request,[]*http.Request)error{return fmt.Errorf("redirect denied")}}})
 ctx,cancel:=context.WithTimeout(context.Background(),120*time.Second);defer cancel()
 head,e:=cli.GetTreeHead(ctx);require(e);kh:=hash(logKeyHash);require(p.VerifyCosignedTreeHead(&kh,&head))
 fetch:=func(x,y uint64)(types.ConsistencyProof,error){return cli.GetConsistencyProof(ctx,requests.ConsistencyProof{OldSize:x,NewSize:y})}
 require(checkFloor(a.TreeHead.TreeHead,b.TreeHead.TreeHead,fetch))
 require(checkFloor(a.TreeHead.TreeHead,head.TreeHead,fetch))
 require(checkFloor(b.TreeHead.TreeHead,head.TreeHead,fetch))
 require(checkFloor(types.TreeHead{Size:retainedSize,RootHash:hash(retainedRoot)},head.TreeHead,fetch))
 require(json.NewEncoder(os.Stdout).Encode(map[string]any{"result":"VERIFIED_COMMON_HEAD","old_index":a.Inclusion.LeafIndex,"new_index":b.Inclusion.LeafIndex,"old_head":a.TreeHead.Size,"new_receipt_head":b.TreeHead.Size,"sampled_tree_size":head.Size,"sampled_tree_root":hex.EncodeToString(head.RootHash[:]),"candidate_message_sha256":hex.EncodeToString(msg[:]),"consistency":"PASS","global_latest":"UNKNOWN","trust_activation":"NO_GO"}))
}
