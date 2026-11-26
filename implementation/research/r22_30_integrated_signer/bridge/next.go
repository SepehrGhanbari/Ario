// Bounded multi-generation adapter. Verify each prior signed witness receipt
// against the pinned member, expected operation history and predecessor digest.
package main
import (
 "bytes";"crypto/ed25519";"fmt";"io";"os";"path/filepath"
 q "ario-r22-26-quorum-gossip"
 w "ario-r22-27-durable-witness"
)
type ChainProof struct { ID string; Receipt *w.Receipt `json:",omitempty"`; Chain []w.Receipt `json:",omitempty"`; Reply q.Reply }
func inputProofs() []ChainProof {
 raw,e:=io.ReadAll(io.LimitReader(os.Stdin,(2<<20)+1));check(e);if len(raw)>2<<20{fail("size")}
 var proofs []ChainProof;decode(raw,&proofs);if len(proofs)!=3{fail("write reservations")};return proofs
}
func rootsArg(raw string) []string {
 var roots []string;decode([]byte(raw),&roots)
 if len(roots)<2||len(roots)>64{fail("history bound")}
 for _,root:=range roots{if !validhash(root){fail("root")}}
 return roots
}
func chainFor(p Pins,proof ChainProof,roots []string) []w.Receipt {
 var m *q.Member
 for i:=range p.Policy.Members{if p.Policy.Members[i].ID==proof.ID{m=&p.Policy.Members[i]}}
 if m==nil{fail("member")}
 c:=config(p,*m)
 chain:=proof.Chain
 if proof.Receipt!=nil {if len(chain)!=0{fail("ambiguous proof")};chain=[]w.Receipt{*proof.Receipt}}
 if len(chain)!=len(roots){fail("history length")}
 prev:=digest(genesis(c))
 for i,r:=range chain{
  unsigned:=r;unsigned.Signature=nil
  if r.Profile!=profile||r.ConfigHash!=digest(c)||r.Request!=(w.Request{Generation:uint64(i+1),Previous:prev,Root:roots[i]})||!ed25519.Verify(m.Key,enc(unsigned),r.Signature){fail("receipt chain")}
  prev=digest(r)
 }
 return chain
}
func nextMode(a []string) bool {
 if len(a)<2{return false}
 if a[1]=="reserve-next"&&len(a)==6{
  dir,pinfile,nonce:=a[2],a[3],a[4];roots:=rootsArg(a[5])
  var p Pins;decode(read(pinfile),&p);validatePins(p)
  if !validhash(nonce){fail("nonce")}
  var c w.Config;decode(read(filepath.Join(dir,"config")),&c)
  var m *q.Member;for i:=range p.Policy.Members{if p.Policy.Members[i].ID==c.Identity{m=&p.Policy.Members[i]}}
  if m==nil||!bytes.Equal(enc(config(p,*m)),enc(c)){fail("pin")}
  proofs:=inputProofs();seen:=map[string]bool{};var own []w.Receipt
  for _,proof:=range proofs{
   if seen[proof.ID]{fail("duplicate member")};seen[proof.ID]=true
   chain:=chainFor(p,proof,roots[:len(roots)-1]);if proof.ID==c.Identity{own=chain}
  }
  if len(own)==0{fail("own prior receipt")}
  key:=ed25519.PrivateKey(read(filepath.Join(dir,"key")))
  req:=w.Request{Generation:uint64(len(roots)),Previous:digest(own[len(own)-1]),Root:roots[len(roots)-1]}
  store:=w.Store{Local:filepath.Join(dir,"local"),Keeper:filepath.Join(dir,"keeper"),Config:c}
  receipt,e:=store.Advance(req,key,nil);check(e)
  st:=q.Statement{Profile:"ARIO-R22.26-READ-v1",Scope:p.Policy.Scope,PolicyHash:digest(p.Policy),Nonce:nonce,Epoch:p.Policy.Epoch,History:roots}
  fmt.Println(string(enc(ChainProof{ID:c.Identity,Chain:append(own,receipt),Reply:q.Reply{ID:c.Identity,Statement:st,Signature:ed25519.Sign(key,enc(st))}})));return true
 }
 if a[1]=="verify-next"&&len(a)==5{
  var p Pins;decode(read(a[2]),&p);validatePins(p)
  nonce,roots:=a[3],rootsArg(a[4]);if !validhash(nonce){fail("nonce")}
  proofs:=inputProofs();seen:=map[string]bool{};replies:=[]q.Reply{}
  for _,proof:=range proofs{
   if seen[proof.ID]||proof.Reply.ID!=proof.ID{fail("member")};seen[proof.ID]=true
   chainFor(p,proof,roots)
   if !bytes.Equal(enc(proof.Reply.Statement.History),enc(roots)){fail("history")}
   replies=append(replies,proof.Reply)
  }
  result:=q.Read(p.Policy,nonce,replies,nil)
  if result.Status!="REVIEWABLE_ONLY"||result.Evidence!=3||result.Floor.Generation!=uint64(len(roots)){fail("quorum")}
  fmt.Println("RESERVATION_CHAIN_VERIFIED_TEST_ONLY");return true
 }
 return false
}
