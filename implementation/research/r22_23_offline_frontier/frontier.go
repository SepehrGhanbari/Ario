package frontier

import (
 "crypto/sha256"
 "fmt"
)

// Hash is a SHA-256 Merkle node digest; callers authenticate heads separately.
type Hash [32]byte
type TreeHead struct { Size uint64; RootHash Hash }
const end uint64=281670
const maxSuffix uint64=8192
const pageSize uint64=128

type frontier struct { size uint64; slots [64]Hash }
func parent(a,b Hash) Hash {
 var buf [65]byte;buf[0]=1;copy(buf[1:33],a[:]);copy(buf[33:],b[:])
 return Hash(sha256.Sum256(buf[:]))
}
func (f *frontier) appendLeaf(h Hash) error {
 if f.size>=1<<63{return fmt.Errorf("frontier size limit")}
 n:=f.size
 for i:=0;i<63;i++{
  if n&(uint64(1)<<i)==0 {f.slots[i]=h;f.size++;return nil}
  h=parent(f.slots[i],h);f.slots[i]=Hash{}
 }
 return fmt.Errorf("frontier overflow")
}
func (f *frontier) root()(Hash,error){
 var h Hash;have:=false
 for i:=0;i<64;i++{
  if f.size&(uint64(1)<<i)!=0{
   if have{h=parent(f.slots[i],h)}else{h=f.slots[i];have=true}
  }
 }
 if !have{return Hash{},fmt.Errorf("empty frontier")}
 return h,nil
}
// The rightmost leaf's RFC6962 inclusion path consists exclusively of
// left siblings at the set-bit positions of size-1, low to high.
func fromLast(size uint64, leaf Hash,path []Hash,want Hash)(frontier,error){
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
func finish(f *frontier, target TreeHead)error{
 if f.size!=target.Size{return fmt.Errorf("incomplete suffix")}
 h,e:=f.root();if e!=nil{return e};if h!=target.RootHash{return fmt.Errorf("suffix root mismatch")};return nil
}
