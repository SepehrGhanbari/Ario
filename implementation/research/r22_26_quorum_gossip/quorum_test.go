package quorum

import("crypto/ed25519";"fmt";"testing")

type fixture struct{p Policy;keys []ed25519.PrivateKey}
func makeFixture(n,q int,epoch uint64)fixture{
 f:=fixture{p:Policy{Scope:"public-synthetic-test",Epoch:epoch,Threshold:q}}
 for i:=0;i<n;i++{
  // Public deterministic TEST seed; never suitable for real signing.
  seed:=make([]byte,32);seed[0]=byte(i+1);seed[1]=byte(epoch)
  k:=ed25519.NewKeyFromSeed(seed);id:=fmt.Sprintf("w%d",i)
  f.keys=append(f.keys,k);f.p.Members=append(f.p.Members,Member{id,fmt.Sprintf("model-domain-%d",i),k.Public().(ed25519.PublicKey)})
 };return f
}
var nonce=hash("test-challenge")
var oldHistory=[]string{hash("receipt-1")}
var newHistory=[]string{hash("receipt-1"),hash("receipt-2")}
func (f fixture) reply(i int,h []string)Reply{return sign(f.p.Members[i].ID,statement(f.p,nonce,h),f.keys[i])}
func expect(t *testing.T,r Result,want string){t.Helper();if r.Status!=want{t.Fatalf("got %s want %s",r.Status,want)}}
func TestTwoOfThreeJointRollbackBoundary(t *testing.T){
 f:=makeFixture(3,2,1)
 // Two compromised witnesses can sign fresh challenges over OLD history.
 // The honest witness is suppressed; no local floor exists.
 r:=Read(f.p,nonce,[]Reply{f.reply(0,oldHistory),f.reply(1,oldHistory)},nil)
 expect(t,r,"REVIEWABLE_ONLY");if r.Floor.Generation!=1{t.Fatal(r)}
}
func TestHonestHigherGossipVeto(t *testing.T){
 f:=makeFixture(3,2,1)
 expect(t,Read(f.p,nonce,[]Reply{f.reply(0,oldHistory),f.reply(1,oldHistory),f.reply(2,newHistory)},nil),"HOLD_WITNESS_DISAGREEMENT")
}
func TestThreeOfThreeTwoRollback(t *testing.T){
 f:=makeFixture(3,3,1)
 expect(t,Read(f.p,nonce,[]Reply{f.reply(0,oldHistory),f.reply(1,oldHistory)},nil),"HOLD_QUORUM")
 expect(t,Read(f.p,nonce,[]Reply{f.reply(0,oldHistory),f.reply(1,oldHistory),f.reply(2,newHistory)},nil),"HOLD_WITNESS_DISAGREEMENT")
 one:=Read(f.p,nonce,[]Reply{f.reply(2,newHistory)},nil);expect(t,one,"HOLD_QUORUM");if one.Floor!=(Floor{})||one.UnadmittedObservation==nil||*one.UnadmittedObservation!=head(newHistory){t.Fatal("single witness evidence lost or admitted")}
 expect(t,Read(f.p,nonce,[]Reply{f.reply(0,newHistory),f.reply(1,newHistory),f.reply(2,newHistory)},nil),"REVIEWABLE_ONLY")
}
func TestThreeOfFourOneFault(t *testing.T){
 f:=makeFixture(4,3,1)
 expect(t,Read(f.p,nonce,[]Reply{f.reply(0,newHistory),f.reply(1,newHistory),f.reply(2,newHistory)},nil),"REVIEWABLE_ONLY")
 expect(t,Read(f.p,nonce,[]Reply{f.reply(0,newHistory),f.reply(1,newHistory),f.reply(2,newHistory),f.reply(3,oldHistory)},nil),"HOLD_WITNESS_DISAGREEMENT")
 expect(t,Read(f.p,nonce,[]Reply{f.reply(0,oldHistory),f.reply(1,oldHistory)},nil),"HOLD_QUORUM")
}
func TestAllCompromisedBoundary(t *testing.T){
 f:=makeFixture(3,3,1)
 expect(t,Read(f.p,nonce,[]Reply{f.reply(0,oldHistory),f.reply(1,oldHistory),f.reply(2,oldHistory)},nil),"REVIEWABLE_ONLY")
}
func TestRetainedFloorAndAlternateHigherHistory(t *testing.T){
 f:=makeFixture(3,2,1);prior:=head(newHistory)
 expect(t,Read(f.p,nonce,[]Reply{f.reply(0,oldHistory),f.reply(1,oldHistory)},&prior),"HOLD_PRIOR_FORK_OR_ROLLBACK")
 fork:=[]string{oldHistory[0],hash("fork"),hash("higher")}
 expect(t,Read(f.p,nonce,[]Reply{f.reply(0,fork),f.reply(1,fork)},&prior),"HOLD_PRIOR_FORK_OR_ROLLBACK")
 newer:=append(append([]string{},newHistory...),hash("receipt-3"))
 expect(t,Read(f.p,nonce,[]Reply{f.reply(0,newer),f.reply(1,newer)},&prior),"REVIEWABLE_ONLY")
}
func TestSignedReplyMutations(t *testing.T){
 f:=makeFixture(3,2,1)
 for _,name:=range []string{"nonce","scope","epoch","policy","profile","signature","history","unknown","duplicate"}{t.Run(name,func(t *testing.T){
  a,b:=f.reply(0,newHistory),f.reply(1,newHistory)
  switch name{
  case "nonce":b.Statement.Nonce=hash("previous-challenge");b=sign(b.ID,b.Statement,f.keys[1])
  case "scope":b.Statement.Scope="other";b=sign(b.ID,b.Statement,f.keys[1])
  case "epoch":b.Statement.Epoch++;b=sign(b.ID,b.Statement,f.keys[1])
  case "policy":b.Statement.PolicyHash=hash("other-policy");b=sign(b.ID,b.Statement,f.keys[1])
  case "profile":b.Statement.Profile="other";b=sign(b.ID,b.Statement,f.keys[1])
  case "signature":b.Signature[0]^=1
  case "history":b.Statement.History=oldHistory
  case "unknown":b.ID="unknown"
  case "duplicate":b=a
  }
  expect(t,Read(f.p,nonce,[]Reply{a,b},nil),"HOLD_REPLY")
 })}
}
func TestDuplicateDomainsKeysAndIDs(t *testing.T){
 for _,name:=range []string{"domain","key","id"}{t.Run(name,func(t *testing.T){
  f:=makeFixture(3,2,1);switch name{case "domain":f.p.Members[1].Domain=f.p.Members[0].Domain;case "key":f.p.Members[1].Key=f.p.Members[0].Key;case "id":f.p.Members[1].ID=f.p.Members[0].ID}
  expect(t,Read(f.p,nonce,nil,nil),"HOLD_POLICY")
 })}
}
func TestIntersectionExhaustive(t *testing.T){
 // Independent enumeration of pairs of masks; all pairs must share > f.
 for n:=1;n<=7;n++{for q:=1;q<=n;q++{for f:=0;f<n;f++{
  want:=true
  count:=func(v int)int{c:=0;for v>0{c+=v&1;v>>=1};return c}
  for a:=1;a<1<<n;a++{if count(a)!=q{continue};for b:=1;b<1<<n;b++{if count(b)==q&&count(a&b)<=f{want=false}}}
  if IntersectionSafe(n,q,f)!=want{t.Fatalf("%d %d %d",n,q,f)}
 }}}
 if IntersectionSafe(3,2,1)||!IntersectionSafe(4,3,1)||IntersectionSafe(4,3,2){t.Fatal("intersection boundary")}
}
func (f fixture) approvals(r Rotation)[]Approval{a:=[]Approval{};for i,k:=range f.keys{a=append(a,approve(f.p.Members[i].ID,r,k))};return a}
func TestRotationControls(t *testing.T){
 old,next:=makeFixture(3,3,1),makeFixture(4,3,2);floor:=head(newHistory);r:=rotation(old.p,next.p,floor,nonce);a,b:=old.approvals(r),next.approvals(r)
 if e:=VerifyRotation(old.p,next.p,floor,nonce,r,a,b);e!=nil{t.Fatal(e)}
 for _,name:=range []string{"two-old","three-new","old-replay","floor","new-policy","nonce","duplicate","signature","epoch-skip"}{t.Run(name,func(t *testing.T){
  x,y,z:=r,append([]Approval{},a...),append([]Approval{},b...);p:=next.p
  switch name{
  case "two-old":y=y[:2]
  case "three-new":z=z[:3]
  case "old-replay":z=y
  case "floor":x.Floor=head(oldHistory);y,z=old.approvals(x),next.approvals(x)
  case "new-policy":p.Threshold=2
  case "nonce":x.Nonce=hash("prior-nonce")
  case "duplicate":y[1]=y[0]
  case "signature":z[0].Signature=append([]byte{},z[0].Signature...);z[0].Signature[0]^=1
  case "epoch-skip":p.Epoch=3
  }
  if VerifyRotation(old.p,p,floor,nonce,x,y,z)==nil{t.Fatal("accepted rotation")}
 })}
}
func TestPublisherKeeperCollusionNotInputs(t *testing.T){
 // Publisher and keeper may present old bytes; neither supplies a witness
 // vote. Model only: no network or separate process is used.
 f:=makeFixture(3,3,1);prior:=head(newHistory)
 r:=Read(f.p,nonce,[]Reply{f.reply(0,newHistory),f.reply(1,newHistory),f.reply(2,newHistory)},&prior)
 expect(t,r,"REVIEWABLE_ONLY");if r.Floor!=prior{t.Fatal(r)}
}

func TestTwoOfThreeOneEquivocatorCanCertifyTwoForks(t *testing.T){
 f:=makeFixture(3,2,1)
 a:=[]string{oldHistory[0],hash("branch-a")}
 b:=[]string{oldHistory[0],hash("branch-b")}
 // w1 equivocates; w0 and w2 each sign just one branch.
 x:=Read(f.p,nonce,[]Reply{f.reply(0,a),f.reply(1,a)},nil)
 y:=Read(f.p,nonce,[]Reply{f.reply(1,b),f.reply(2,b)},nil)
 expect(t,x,"REVIEWABLE_ONLY");expect(t,y,"REVIEWABLE_ONLY")
 if x.Floor.Generation!=y.Floor.Generation||x.Floor.Hash==y.Floor.Hash{t.Fatal("expected conflicting quorum heads")}
 expect(t,Read(f.p,nonce,[]Reply{f.reply(0,a),f.reply(1,b),f.reply(2,b)},nil),"HOLD_WITNESS_DISAGREEMENT")
}
func TestOldEpochRepliesCannotAuthorizeNewPolicy(t *testing.T){
 old,next:=makeFixture(3,3,1),makeFixture(3,3,2)
 expect(t,Read(next.p,nonce,[]Reply{old.reply(0,newHistory),old.reply(1,newHistory),old.reply(2,newHistory)},nil),"HOLD_REPLY")
}
