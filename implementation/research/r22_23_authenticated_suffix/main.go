// R22.23: authenticated suffix scan using retained Merkle frontier. Research only.
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
const end uint64=281670
const firstRoot="628a11eff388e4d381e43a62effaa07362ef0aaf8d43ad9e09289630a4c05836"
const retainedRoot="dafc6911b16d150b1628937dd5030ba1b188b6ffe916837d41db37e4b867cefc"
const firstChecksum="46aae12df174dd36537e66612a9c51cd9c8c114569ed89d2093c7da47597c3b4"
const laterChecksum="e0f0e3c939401d4f39498a82613f5073f66fe829ef89a1441af03520e9938ab7"
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
func checkRange(size uint64,ms []match)error{
 if size<end||len(ms)!=2||ms[0]!=(match{start,firstChecksum})||ms[1]!=(match{start+1,laterChecksum}) {return fmt.Errorf("retained range mismatch")}
 return nil
}

const maxSuffix uint64=8192
const pageSize uint64=128
type frontier struct { size uint64; slots [64]crypto.Hash }
func parent(a,b crypto.Hash) crypto.Hash {
 var buf [65]byte;buf[0]=1;copy(buf[1:33],a[:]);copy(buf[33:],b[:])
 return crypto.Hash(sha256.Sum256(buf[:]))
}
func (f *frontier) appendLeaf(h crypto.Hash) error {
 if f.size>=1<<63{return fmt.Errorf("frontier size limit")}
 n:=f.size
 for i:=0;i<63;i++{
  if n&(uint64(1)<<i)==0 {f.slots[i]=h;f.size++;return nil}
  h=parent(f.slots[i],h);f.slots[i]=crypto.Hash{}
 }
 return fmt.Errorf("frontier overflow")
}
func (f *frontier) root()(crypto.Hash,error){
 var h crypto.Hash;have:=false
 for i:=0;i<64;i++{
  if f.size&(uint64(1)<<i)!=0{
   if have{h=parent(f.slots[i],h)}else{h=f.slots[i];have=true}
  }
 }
 if !have{return crypto.Hash{},fmt.Errorf("empty frontier")}
 return h,nil
}
// The rightmost leaf's RFC6962 inclusion path consists exclusively of
// left siblings at the set-bit positions of size-1, low to high.
func fromLast(size uint64, leaf crypto.Hash,path []crypto.Hash,want crypto.Hash)(frontier,error){
 var f frontier
 if size==0||size>=1<<63{return f,fmt.Errorf("invalid anchor size")}
 f.size=size-1;j:=0
 for i:=0;i<63;i++{
  if f.size&(uint64(1)<<i)!=0{
   if j>=len(path){return frontier{},fmt.Errorf("short rightmost proof")}
   f.slots[i]=path[j];j++
  }
 }
 if j!=len(path){return frontier{},fmt.Errorf("long rightmost proof")}
 if e:=f.appendLeaf(leaf);e!=nil{return frontier{},e}
 h,e:=f.root();if e!=nil||h!=want{return frontier{},fmt.Errorf("anchor root mismatch")}
 return f,nil
}
func pageEnd(cursor,target uint64)(uint64,error){
 if target<end||target-end>maxSuffix||cursor<end||cursor>=target{return 0,fmt.Errorf("scan budget/position")}
 if target-cursor>pageSize{return cursor+pageSize,nil}
 return target,nil
}
func finish(f *frontier, target types.TreeHead)error{
 if f.size!=target.Size{return fmt.Errorf("incomplete suffix")}
 h,e:=f.root();if e!=nil{return e};if h!=target.RootHash{return fmt.Errorf("suffix root mismatch")};return nil
}
func main(){
 if len(os.Args)!=1{log.Fatal("HOLD: no caller endpoint")}
 raw,e:=os.ReadFile("bootstrap.json");require(e);if len(raw)>4096{log.Fatal("HOLD: bootstrap oversize")}
 var b bootstrap;d:=json.NewDecoder(strings.NewReader(string(raw)));d.DisallowUnknownFields();require(d.Decode(&b))
 var extra any;if d.Decode(&extra)!=io.EOF{log.Fatal("HOLD: trailing bootstrap")}
 if b!=(bootstrap{Start:start,Size:start+1,Root:firstRoot,Public:signer,First:firstChecksum}){log.Fatal("HOLD: bootstrap pin mismatch")}
 p,e:=policy.ParseConfig(strings.NewReader(policyText));require(e)
 pk,e:=hex.DecodeString(signer);require(e);var pub crypto.PublicKey;copy(pub[:],pk)
 keyHash:=crypto.Hash(sha256.Sum256(pub[:]))
 kh:=hash(logKeyHash)
 cli:=client.New(client.Config{URL:logURL,HTTPClient:&http.Client{Timeout:12*time.Second,CheckRedirect:func(*http.Request,[]*http.Request)error{return fmt.Errorf("redirect denied")}}})
 ctx,cancel:=context.WithTimeout(context.Background(),180*time.Second);defer cancel()
 cth,e:=cli.GetTreeHead(ctx);require(e);require(p.VerifyCosignedTreeHead(&kh,&cth))
 old:=types.TreeHead{Size:end,RootHash:hash(retainedRoot)}
 fetch:=func(a,b uint64)(types.ConsistencyProof,error){return cli.GetConsistencyProof(ctx,requests.ConsistencyProof{OldSize:a,NewSize:b})}
 require(checkFloor(types.TreeHead{Size:start+1,RootHash:hash(firstRoot)},cth.TreeHead,fetch))
 require(checkFloor(old,cth.TreeHead,fetch))
 if cth.Size-end>maxSuffix{log.Fatal("HOLD: suffix exceeds bounded scan budget")}
 // Verify both historical leaves at the retained head, then derive a
 // frontier from the last one. Its inclusion proof is not a fresh pin.
 matches:=[]match{}
 var acc frontier
 for i:=start;i<end;i++{
  leaves,e:=cli.GetLeaves(ctx,requests.Leaves{StartIndex:i,EndIndex:i+1});require(e)
  if len(leaves)!=1{log.Fatal("HOLD: historical leaf page")}
  leaf:=leaves[0];h:=leaf.ToHash()
  pr,e:=cli.GetInclusionProof(ctx,requests.InclusionProof{Size:end,LeafHash:h});require(e)
  if pr.LeafIndex!=i||leaf.KeyHash!=keyHash||!leaf.Verify(&pub){log.Fatal("HOLD: historical leaf identity")}
  require(pr.Verify(&h,&old))
  matches=append(matches,match{i,hex.EncodeToString(leaf.Checksum[:])})
  if i==end-1{acc,e=fromLast(end,h,pr.Path,old.RootHash);require(e)}
 }
 require(checkRange(cth.Size,matches))
 // No per-leaf network inclusion proof is needed. Every returned leaf hash
 // is committed by the final reconstructed root; no result is emitted
 // before that check succeeds. Unrelated submitters are not authenticated
 // individually; only matching signer leaves need signature verification.
 cursor:=end;pages:=0;newMatches:=[]match{}
 for cursor<cth.Size{
  stop,e:=pageEnd(cursor,cth.Size);require(e)
  leaves,e:=cli.GetLeaves(ctx,requests.Leaves{StartIndex:cursor,EndIndex:stop});require(e)
  if len(leaves)==0||uint64(len(leaves))>stop-cursor{log.Fatal("HOLD: empty or oversize suffix page")}
  pages++
  for _,leaf:=range leaves{
   require(acc.appendLeaf(leaf.ToHash()))
   if leaf.KeyHash==keyHash{
    if !leaf.Verify(&pub){log.Fatal("HOLD: matching signer signature invalid")}
    newMatches=append(newMatches,match{cursor,hex.EncodeToString(leaf.Checksum[:])})
   }
   cursor++
  }
 }
 require(finish(&acc,cth.TreeHead))
 disposition:="NO_NEW_MATCH_IN_SAMPLED_SUFFIX"
 if len(newMatches)>0{disposition="HOLD_OPAQUE_NEW_SIGNED_COMMITMENT"}
 require(json.NewEncoder(os.Stdout).Encode(map[string]any{
  "result":"AUTHENTICATED_COMPLETE_SAMPLED_SUFFIX", "disposition":disposition,
  "sampled_tree_size":cth.Size,"sampled_tree_root":hex.EncodeToString(cth.RootHash[:]),
  "retained_tree_size":end,"retained_floor_consistency":"PASS","bootstrap_consistency":"PASS",
  "scan_start":end,"scan_end_exclusive":cursor,"verified_suffix_leaf_count":cursor-end,
  "page_count":pages,"max_suffix_leaves":maxSuffix,"retained_matches":matches,"new_matching_signed_leaves":newMatches,
  "complete_sampled_suffix":true,"reconstructed_root":"MATCH",
  "global_latest":"NOT_ESTABLISHED","freshness":"UNKNOWN","history_truth":"UNKNOWN","trust_activation":"NO_GO","production":"NO_GO","merge_authorized":false,
 }))
}
