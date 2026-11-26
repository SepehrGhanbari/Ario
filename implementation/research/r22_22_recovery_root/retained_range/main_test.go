package main
import("testing";"fmt";"crypto/sha256";"sigsum.org/sigsum-go/pkg/crypto";"sigsum.org/sigsum-go/pkg/types")
func node(a,b crypto.Hash)crypto.Hash{buf:=append([]byte{1},a[:]...);return crypto.Hash(sha256.Sum256(append(buf,b[:]...)))}
func TestFloor(t *testing.T){
 a:=crypto.Hash(sha256.Sum256([]byte{0,1}));b:=crypto.Hash(sha256.Sum256([]byte{0,2}));old:=types.TreeHead{Size:1,RootHash:a};next:=types.TreeHead{Size:2,RootHash:node(a,b)}
 good:=types.ConsistencyProof{Path:[]crypto.Hash{b}};bad:=types.ConsistencyProof{Path:[]crypto.Hash{a}}
 cases:=[]struct{name string;head types.TreeHead;proof types.ConsistencyProof;err error;want bool;calls int}{
 {"same",old,good,nil,true,0},{"stale",types.TreeHead{},good,nil,false,0},{"fork",types.TreeHead{Size:1,RootHash:b},good,nil,false,0},
 {"advance-real-merkle",next,good,nil,true,1},{"advance-tampered",next,bad,nil,false,1},{"advance-missing",next,types.ConsistencyProof{},fmt.Errorf("offline"),false,1},{"advance-empty",next,types.ConsistencyProof{},nil,false,1}}
 for _,c:=range cases{t.Run(c.name,func(t *testing.T){calls:=0;e:=checkFloor(old,c.head,func(x,y uint64)(types.ConsistencyProof,error){calls++;if x!=1||y!=c.head.Size{t.Fatal("wrong proof coordinates")};return c.proof,c.err});if (e==nil)!=c.want||calls!=c.calls{t.Fatalf("err=%v calls=%d",e,calls)}})}
}
func TestRange(t *testing.T){
 good:=[]match{{start,firstChecksum},{start+1,laterChecksum}}
 for _,s:=range []uint64{end,end+1,end+100000,1<<62}{if e:=checkRange(s,good);e!=nil{t.Fatal(e)}}
 cases:=[][]match{nil,good[:1],{{start,firstChecksum},{start+1,firstChecksum}},{{start+1,laterChecksum},{start,firstChecksum}},append(append([]match{},good...),match{end,laterChecksum})}
 for i,c:=range cases{if checkRange(end,c)==nil{t.Fatalf("accepted bad range %d",i)}}
 if checkRange(end-1,good)==nil{t.Fatal("stale head")}
}
