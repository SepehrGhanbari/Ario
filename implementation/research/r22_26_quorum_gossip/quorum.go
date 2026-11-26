// R22.26 synthetic quorum/gossip model. No live authority or external service.
package quorum

import (
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "fmt"
)

type Member struct { ID, Domain string; Key ed25519.PublicKey }
type Policy struct { Scope string; Epoch uint64; Threshold int; Members []Member }
type Floor struct { Generation uint64; Hash string }
type Statement struct { Profile, Scope, PolicyHash, Nonce string; Epoch uint64; History []string }
type Reply struct { ID string; Statement Statement; Signature []byte }
type Result struct { Status string; Floor Floor; Evidence int }

func hash(v any) string { b,_:=json.Marshal(v);h:=sha256.Sum256(b);return hex.EncodeToString(h[:]) }
func validHash(s string)bool{b,e:=hex.DecodeString(s);return e==nil&&len(b)==32&&hex.EncodeToString(b)==s}
func valid(p Policy)bool{
 if p.Scope==""||p.Epoch==0||len(p.Members)<1||len(p.Members)>16||p.Threshold<1||p.Threshold>len(p.Members){return false}
 ids,domains,keys:=map[string]bool{},map[string]bool{},map[string]bool{}
 for _,m:=range p.Members{
  k:=hex.EncodeToString(m.Key)
  if m.ID==""||m.Domain==""||len(m.Key)!=ed25519.PublicKeySize||ids[m.ID]||domains[m.Domain]||keys[k]{return false}
  ids[m.ID]=true;domains[m.Domain]=true;keys[k]=true
 }
 return true
}
func payload(s Statement)[]byte{b,_:=json.Marshal(s);return b}
func sign(id string,s Statement,k ed25519.PrivateKey)Reply{return Reply{id,s,ed25519.Sign(k,payload(s))}}
func statement(p Policy,nonce string,history []string)Statement{return Statement{"ARIO-R22.26-READ-v1",p.Scope,hash(p),nonce,p.Epoch,history}}
func head(h []string)Floor{
 // Hash chain over every receipt digest: bind prefix, order and length.
 prev:="ARIO-R22.26-GENESIS";for _,r:=range h{prev=hash([]string{prev,r})};return Floor{uint64(len(h)),prev}
}
func hold(reason string,n int)Result{return Result{"HOLD_"+reason,Floor{},n}}
// All supplied replies are checked. Any signed disagreement is HOLD, never
// discard a higher or conflicting observation to construct a matching quorum.
// Missing responses are allowed only by the explicitly pinned threshold.
func Read(p Policy,nonce string,replies []Reply,prior *Floor)Result{
 if !valid(p)||!validHash(nonce)||len(replies)>len(p.Members){return hold("POLICY",0)}
 if prior!=nil&&(prior.Generation==0||!validHash(prior.Hash)){return hold("PRIOR",0)}
 keys:=map[string]ed25519.PublicKey{};for _,m:=range p.Members{keys[m.ID]=m.Key}
 seen:=map[string]bool{};var selected []string;var selectedHash string
 for _,r:=range replies{
  k,ok:=keys[r.ID];s:=r.Statement
  if !ok||seen[r.ID]||s.Profile!="ARIO-R22.26-READ-v1"||s.Scope!=p.Scope||s.PolicyHash!=hash(p)||s.Epoch!=p.Epoch||s.Nonce!=nonce||len(s.History)==0||len(s.History)>4096||!ed25519.Verify(k,payload(s),r.Signature){return hold("REPLY",len(seen))}
  for _,x:=range s.History{if !validHash(x){return hold("HISTORY",len(seen))}}
  seen[r.ID]=true
  if prior!=nil&&(uint64(len(s.History))<prior.Generation||head(s.History[:prior.Generation])!=*prior){return hold("PRIOR_FORK_OR_ROLLBACK",len(seen))}
  h:=hash(s.History)
  if selected==nil{selected=s.History;selectedHash=h}else if h!=selectedHash{return hold("WITNESS_DISAGREEMENT",len(seen))}
 }
 if len(seen)<p.Threshold{return hold("QUORUM",len(seen))}
 return Result{"REVIEWABLE_ONLY",head(selected),len(seen)}
}
// Minimum intersection of two quorums. Honest durable non-equivocation
// must be established separately; this is only an arithmetic condition.
func IntersectionSafe(n,q,f int)bool{return n>0&&q>0&&q<=n&&f>=0&&f<n&&2*q-n>f}

type Rotation struct {Profile,Scope,OldPolicyHash,NewPolicyHash,Nonce string; OldEpoch,NewEpoch uint64; Floor Floor}
type Approval struct{ID string; Signature []byte}
func rotation(old,next Policy,f Floor,nonce string)Rotation{return Rotation{"ARIO-R22.26-ROTATION-v1",old.Scope,hash(old),hash(next),nonce,old.Epoch,next.Epoch,f}}
func rotationBytes(r Rotation)[]byte{b,_:=json.Marshal(r);return b}
func approve(id string,r Rotation,k ed25519.PrivateKey)Approval{return Approval{id,ed25519.Sign(k,rotationBytes(r))}}
func unanimous(p Policy,r Rotation,a []Approval)bool{
 if len(a)!=len(p.Members){return false}
 keys:=map[string]ed25519.PublicKey{};for _,m:=range p.Members{keys[m.ID]=m.Key}
 seen:=map[string]bool{};for _,x:=range a{k,ok:=keys[x.ID];if !ok||seen[x.ID]||!ed25519.Verify(k,rotationBytes(r),x.Signature){return false};seen[x.ID]=true};return true
}
// Conservative rotation model: old and new entire sets sign exactly the
// same transition, binding independently retained prior policy and floor.
// No automatic replacement if an old witness disappears.
func VerifyRotation(old,next Policy,prior Floor,nonce string,r Rotation,oldA,newA []Approval)error{
 if !valid(old)||!valid(next)||old.Scope!=next.Scope||old.Epoch==^uint64(0)||next.Epoch!=old.Epoch+1||!validHash(nonce)||prior.Generation==0||!validHash(prior.Hash)||r!=rotation(old,next,prior,nonce){return fmt.Errorf("HOLD_ROTATION_BINDING")}
 if !unanimous(old,r,oldA)||!unanimous(next,r,newA){return fmt.Errorf("HOLD_ROTATION_APPROVAL")}
 return nil
}
