package main
import("testing";"os";"path/filepath";"encoding/json";"crypto/sha256";"fmt";"math/bits";"sigsum.org/sigsum-go/pkg/crypto";"sigsum.org/sigsum-go/pkg/types")
func fixture(n int)[]crypto.Hash{
 a:=make([]crypto.Hash,n)
 for i:=range a{a[i]=crypto.Hash(sha256.Sum256([]byte(fmt.Sprintf("synthetic-leaf-%d",i))))}
 return a
}
// Independent recursive RFC6962 shape, not the frontier implementation.
func refRoot(a []crypto.Hash)crypto.Hash{
 if len(a)==1{return a[0]}
 k:=1<<(bits.Len(uint(len(a)-1))-1)
 l,r:=refRoot(a[:k]),refRoot(a[k:])
 data:=append([]byte{1},l[:]...);data=append(data,r[:]...)
 return crypto.Hash(sha256.Sum256(data))
}
func refLastPath(a []crypto.Hash)[]crypto.Hash{
 if len(a)==1{return nil}
 k:=1<<(bits.Len(uint(len(a)-1))-1)
 return append(refLastPath(a[k:]),refRoot(a[:k]))
}
func TestFrontierAcrossTreeShapes(t *testing.T){
 all:=fixture(520)
 for n:=1;n<=257;n++{
  f,e:=fromLast(uint64(n),all[n-1],refLastPath(all[:n]),refRoot(all[:n]));if e!=nil{t.Fatalf("size %d: %v",n,e)}
  for j:=n;j<n+12;j++{if e=f.appendLeaf(all[j]);e!=nil{t.Fatal(e)}
   if e=finish(&f,types.TreeHead{Size:uint64(j+1),RootHash:refRoot(all[:j+1])});e!=nil{t.Fatalf("size %d->%d: %v",n,j+1,e)}
  }
 }
}
func TestAnchorMutations(t *testing.T){
 a:=fixture(31);p:=refLastPath(a);r:=refRoot(a)
 bad:=append([]crypto.Hash{},p...);bad[0][0]^=1
 cases:=[]struct{name string;n uint64;leaf crypto.Hash;path []crypto.Hash;root crypto.Hash}{
  {"short",31,a[30],p[:len(p)-1],r},{"extra",31,a[30],append(append([]crypto.Hash{},p...),a[0]),r},
  {"tampered",31,a[30],bad,r},{"wrong-leaf",31,a[29],p,r},{"wrong-root",31,a[30],p,a[0]},
  {"zero",0,a[30],p,r},{"oversize",1<<63,a[30],p,r},
 }
 for _,c:=range cases{t.Run(c.name,func(t *testing.T){if _,e:=fromLast(c.n,c.leaf,c.path,c.root);e==nil{t.Fatal("accepted")}})}
}
func TestSuffixMutations(t *testing.T){
 a:=fixture(19);old:=a[:11];target:=types.TreeHead{Size:19,RootHash:refRoot(a)}
 good:=a[11:];reorder:=append([]crypto.Hash{},good...);reorder[0],reorder[1]=reorder[1],reorder[0]
 duplicate:=append([]crypto.Hash{},good...);duplicate[1]=duplicate[0]
 modified:=append([]crypto.Hash{},good...);modified[4][0]^=1
 cases:=[]struct{name string;leaves []crypto.Hash;ok bool}{
  {"exact",good,true},{"missing",good[:7],false},{"reorder",reorder,false},{"duplicate",duplicate,false},
  {"modified",modified,false},{"extra",append(append([]crypto.Hash{},good...),a[0]),false},
 }
 for _,c:=range cases{t.Run(c.name,func(t *testing.T){f,e:=fromLast(11,old[10],refLastPath(old),refRoot(old));if e!=nil{t.Fatal(e)};for _,h:=range c.leaves{if e=f.appendLeaf(h);e!=nil{t.Fatal(e)}};if (finish(&f,target)==nil)!=c.ok{t.Fatal("incorrect decision")}})}
}
func TestPageBoundaries(t *testing.T){
 for _,c:=range []struct{cursor,target,want uint64;ok bool}{
  {end,end+1,end+1,true},{end,end+1000,end+128,true},{end+999,end+1000,end+1000,true},
  {end,end+maxSuffix,end+128,true},{end,end+maxSuffix+1,end+128,true},{end,end,0,false},
  {end-1,end+1,0,false},{end,end-1,0,false},{end+2,end+1,0,false},
 }{got,e:=pageEnd(c.cursor,c.target);if (e==nil)!=c.ok||got!=c.want{t.Fatalf("page %v => %d %v",c,got,e)}}
}

func sampleState()checkpoint{
 return checkpoint{profile,end,retainedRoot,signer,end+100,hash(retainedRoot),end+10,[64]crypto.Hash{},[]match{{end+1,firstChecksum}}}
}
func statePin(b []byte)string{return fmt.Sprintf("%x",sha256.Sum256(b))}
func TestCheckpointPins(t *testing.T){
 s:=sampleState();raw,e:=encodeState(s);if e!=nil{t.Fatal(e)}
 pin:=statePin(raw);got,e:=loadState(raw,pin);if e!=nil||got.Cursor!=s.Cursor{t.Fatal(e)}
 for _,name:=range []string{"cursor","frontier","target","match-erasure","match-substitution","signer","anchor","rollback"}{
  t.Run(name,func(t *testing.T){
   x:=sampleState()
   switch name{
   case "cursor":x.Cursor++
   case "frontier":x.Slots[1][0]^=1
   case "target":x.TargetRoot[0]^=1
   case "match-erasure":x.Matches=[]match{}
   case "match-substitution":x.Matches[0].Checksum=laterChecksum
   case "signer":x.Signer=firstChecksum
   case "anchor":x.AnchorRoot=firstChecksum
   case "rollback":x.Cursor=end;x.Matches=[]match{}
   }
   b,_:=json.Marshal(x);if _,e:=loadState(b,pin);e==nil{t.Fatal("accepted altered state with retained digest")}
  })
 }
 if _,e=loadState(raw,"");e==nil{t.Fatal("missing pin")}
 if _,e=loadState(append(raw,'\n'),statePin(append(raw,'\n')));e==nil{t.Fatal("noncanonical")}
 // Explicit trust boundary: an attacker controlling both bytes and digest
 // can remove the matching observations. The Merkle frontier alone cannot
 // authenticate their completeness; this is why the external pin is required.
 x:=sampleState();x.Matches=[]match{};b,e:=encodeState(x);if e!=nil{t.Fatal(e)}
 if _,e=loadState(b,statePin(b));e!=nil{t.Fatal("boundary control",e)}
}
func TestCheckpointSchema(t *testing.T){
 for _,name:=range []string{"unknown","duplicate","trailing","wrong-index","wrong-order","inactive-slot","null-matches","cursor-past-target","target-overflow"}{
  t.Run(name,func(t *testing.T){
   x:=sampleState();var b []byte
   switch name{
   case "unknown":raw,_:=json.Marshal(x);b=append(append([]byte{},raw[:len(raw)-1]...),[]byte(",\"Unknown\":1}")...)
   case "duplicate":raw,_:=json.Marshal(x);b=append(append([]byte{},raw[:len(raw)-1]...),[]byte(",\"Profile\":\""+profile+"\"}")...)
   case "trailing":raw,_:=json.Marshal(x);b=append(raw,[]byte("{}")...)
   case "wrong-index":x.Matches[0].Index=x.Cursor
   case "wrong-order":x.Matches=append(x.Matches,x.Matches[0])
   case "inactive-slot":x.Slots[63][0]=1
   case "null-matches":x.Matches=nil
   case "cursor-past-target":x.Cursor=x.TargetSize+1
   case "target-overflow":x.TargetSize=1<<63
   }
   if b==nil{b,_=json.Marshal(x)}
   if _,e:=loadState(b,statePin(b));e==nil{t.Fatal("accepted bad schema")}
  })
 }
}
func TestDurableNoOverwrite(t *testing.T){
 p:=filepath.Join(t.TempDir(),"next-checkpoint.json")
 s:=sampleState();pin,e:=saveState(p,s);if e!=nil{t.Fatal(e)}
 raw,e:=os.ReadFile(p);if e!=nil||statePin(raw)!=pin{t.Fatal("written digest")}
 s.Matches=[]match{};if _,e=saveState(p,s);e==nil{t.Fatal("overwrote checkpoint")}
 after,e:=os.ReadFile(p);if e!=nil||statePin(after)!=pin{t.Fatal("previous checkpoint changed")}
}
func TestResumeRequiresPrefixProof(t *testing.T){
 s:=sampleState()
 // A schema-valid arbitrary frontier cannot be accepted as a prefix.
 cur:=types.TreeHead{Size:s.TargetSize,RootHash:s.TargetRoot}
 calls:=0
 e:=authenticateState(s,cur,func(a,b uint64)(types.ConsistencyProof,error){calls++;return types.ConsistencyProof{},nil})
 if e==nil||calls!=1{t.Fatalf("bad proof accepted %v %d",e,calls)}
 stale:=types.TreeHead{Size:s.TargetSize-1,RootHash:s.TargetRoot}
 calls=0;e=authenticateState(s,stale,func(a,b uint64)(types.ConsistencyProof,error){calls++;return types.ConsistencyProof{},nil})
 if e==nil||calls!=0{t.Fatal("stale target")}
}
