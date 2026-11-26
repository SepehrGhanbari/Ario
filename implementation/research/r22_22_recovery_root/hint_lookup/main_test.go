package main
import("testing";"fmt";"os";"encoding/json";"encoding/hex";"sigsum.org/sigsum-go/pkg/crypto";"sigsum.org/sigsum-go/pkg/types")
func TestActualHintSignatures(t *testing.T){
 raw,e:=os.ReadFile("hints.json");if e!=nil{t.Fatal(e)};var hs []hint;if e=json.Unmarshal(raw,&hs);e!=nil||len(hs)!=5{t.Fatal("fixture")}
 k,_:=hex.DecodeString(signer);var pub crypto.PublicKey;copy(pub[:],k)
 for i,h:=range hs{_,e:=leafFromHint(h,pub);want:=i==0||i==1||i==4;if (e==nil)!=want{t.Fatalf("case %d error %v",i,e)}}
 calls:=0;get:=func(crypto.Hash)(types.InclusionProof,error){calls++;return types.InclusionProof{},fmt.Errorf("missing proof")}
 head:=types.TreeHead{Size:floorSize,RootHash:hash(retainedRoot)}
 for i,h:=range hs{_,e:=locate(h,pub,head,get);if e==nil{t.Fatalf("accepted missing proof %d",i)}}
 if calls!=3{t.Fatal(calls)}
}
func TestWrongMerkleProof(t *testing.T){
 raw,_:=os.ReadFile("hints.json");var hs []hint;json.Unmarshal(raw,&hs);k,_:=hex.DecodeString(signer);var pub crypto.PublicKey;copy(pub[:],k)
 h:=hs[1];leaf,e:=leafFromHint(h,pub);if e!=nil{t.Fatal(e)};digest:=leaf.ToHash()
 get:=func(v crypto.Hash)(types.InclusionProof,error){if v!=digest{t.Fatal("wrong request hash")};return types.InclusionProof{LeafIndex:start+1,Path:[]crypto.Hash{digest}},nil}
 if _,e=locate(h,pub,types.TreeHead{Size:floorSize,RootHash:hash(retainedRoot)},get);e==nil{t.Fatal("invalid proof accepted")}
}
