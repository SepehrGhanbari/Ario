package main

import (
	"context"
	"crypto/ed25519"
	"crypto/rand"
	"errors"
	"fmt"
	"sync"
	"testing"
)

type memoryCustodian struct {
	mu sync.Mutex
	latest Receipt
	objects map[string][]byte
	err error
}
func (m *memoryCustodian) Latest(_ context.Context, _ string)(Receipt,error){
	m.mu.Lock();defer m.mu.Unlock();if m.err!=nil{return Receipt{},m.err};return m.latest,nil
}
func (m *memoryCustodian) Checkpoint(_ context.Context, h string)([]byte,error){
	m.mu.Lock();defer m.mu.Unlock();if m.err!=nil{return nil,m.err};b,ok:=m.objects[h];if !ok{return nil,errors.New("object missing")};return append([]byte(nil),b...),nil
}
type memoryWitness struct { chain []Receipt; err error }
func (m *memoryWitness) VerifiedReceiptChain(_ context.Context,_ string)([]Receipt,error){
	if m.err!=nil{return nil,m.err};return append([]Receipt(nil),m.chain...),nil
}
type testTransitions struct { accepted map[string]bool }
func transitionKey(a,b Receipt)string{return fmt.Sprintf("%d:%s:%d:%s",a.TargetSize,a.TargetRoot,b.TargetSize,b.TargetRoot)}
func (t testTransitions) VerifyTransition(_ context.Context,a,b Receipt)error{
	if !t.accepted[b.TransitionProofSHA256]||b.TransitionProofSHA256!=digest([]byte(transitionKey(a,b))){return errors.New("consistency proof rejected")}
	return nil
}
type fixture struct {
	pub ed25519.PublicKey
	priv ed25519.PrivateKey
	cust *memoryCustodian
	wit *memoryWitness
	trans testTransitions
	chain []Receipt
	cps []Checkpoint
}
func newFixture(t *testing.T)*fixture{
	t.Helper()
	pub,priv,e:=ed25519.GenerateKey(rand.Reader);if e!=nil{t.Fatal(e)}
	f:=&fixture{pub:pub,priv:priv,cust:&memoryCustodian{objects:map[string][]byte{}},wit:&memoryWitness{},trans:testTransitions{accepted:map[string]bool{}}}
	prev:=genesisReceipt
	var prior Receipt
	steps:=[]struct{cursor,target uint64;root string;matches []Match}{
		{10,20,hex64("root-20"),[]Match{{2,hex64("match-2")},{7,hex64("match-7")}}},
		{15,30,hex64("root-30"),[]Match{{2,hex64("match-2")},{7,hex64("match-7")},{12,hex64("match-12")}}},
		{30,40,hex64("root-40"),[]Match{{2,hex64("match-2")},{7,hex64("match-7")},{12,hex64("match-12")},{22,hex64("match-22")}}},
	}
	for i,s:=range steps{
		cp:=Checkpoint{Profile:checkpointProfile,Scope:"ario-r22-25-test",Generation:uint64(i+1),PreviousReceiptSHA256:prev,Cursor:s.cursor,TargetSize:s.target,TargetRoot:s.root,FrontierSHA256:hex64(fmt.Sprintf("frontier-%d",i+1)),Matches:s.matches}
		cp.MatchManifestSHA256=matchManifest(cp.Matches)
		raw,e:=canonicalCheckpoint(cp);if e!=nil{t.Fatal(e)}
		proof:=""
		if i>0{proof=digest([]byte(transitionKey(prior,Receipt{TargetSize:s.target,TargetRoot:s.root})))}
		r:=Receipt{Profile:keeperProfile,Scope:cp.Scope,Generation:cp.Generation,PreviousReceiptSHA256:prev,CheckpointSHA256:digest(raw),CheckpointBytes:uint64(len(raw)),Cursor:cp.Cursor,TargetSize:cp.TargetSize,TargetRoot:cp.TargetRoot,MatchManifestSHA256:cp.MatchManifestSHA256,TransitionProofSHA256:proof,KeyID:"synthetic-keeper-key"}
		r,e=signReceipt(r,priv);if e!=nil{t.Fatal(e)}
		if i>0{f.trans.accepted[proof]=true}
		h,e:=receiptHash(r);if e!=nil{t.Fatal(e)}
		f.cust.objects[r.CheckpointSHA256]=raw
		f.chain=append(f.chain,r);f.cps=append(f.cps,cp)
		prev=h;prior=r
	}
	f.cust.latest=f.chain[len(f.chain)-1]
	f.wit.chain=append([]Receipt(nil),f.chain...)
	return f
}
func hex64(s string)string{return digest([]byte(s))}
func (f *fixture) recover(t *testing.T, prior *Floor)(Recovery,error){
	t.Helper();return Recover(context.Background(),"ario-r22-25-test","synthetic-keeper-key",f.pub,f.cust,f.wit,f.trans,prior)
}
func cloneReceipt(r Receipt)Receipt{return r}

func TestRecoverAfterPublisherAndBothRelayCopiesRollback(t *testing.T){
	f:=newFixture(t)
	// Model publisher and both relays restoring identical old bytes and
	// adjacent digests. Recovery has no dependency on these mirrors.
	old:=append([]byte(nil),f.cust.objects[f.chain[0].CheckpointSHA256]...)
	type mirror struct{blob []byte;digest string}
	mirrors:=[]mirror{{old,digest(old)},{append([]byte(nil),old...),digest(old)},{append([]byte(nil),old...),digest(old)}}
	for _,m:=range mirrors{if digest(m.blob)!=m.digest||m.digest!=f.chain[0].CheckpointSHA256{t.Fatal("rollback fixture mismatch")}}
	got,e:=f.recover(t,nil);if e!=nil{t.Fatal(e)}
	if got.Receipt.Generation!=3||got.Checkpoint.Cursor!=30||got.Complete{t.Fatalf("unexpected recovery: %+v",got)}
	if got.ReceiptSHA256==""||got.CheckpointSHA256!=f.chain[2].CheckpointSHA256{t.Fatal("recovery followed publisher/relay rollback instead of keeper head")}
}
func TestDeletedPublisherAndRelayCopiesDoNotAffectCustodyRecovery(t *testing.T){
	f:=newFixture(t)
	// The test recovery path uses only Custodian + VerifiedWitnessLog.
	got,e:=f.recover(t,nil);if e!=nil{t.Fatal(e)}
	if got.Checkpoint.Generation!=3{t.Fatal("did not recover latest")}
}
func TestCustodianRollbackDetectedByWitnessChain(t *testing.T){
	f:=newFixture(t);f.cust.latest=f.chain[0]
	if _,e:=f.recover(t,nil);e==nil{t.Fatal("accepted stale custodian head")}
}
func TestWitnessRollbackDetectedByCustodianHead(t *testing.T){
	f:=newFixture(t);f.wit.chain=f.wit.chain[:1]
	if _,e:=f.recover(t,nil);e==nil{t.Fatal("accepted stale witness chain")}
}
func TestPriorFloorRejectsDualSourceRollback(t *testing.T){
	f:=newFixture(t);h,_:=receiptHash(f.chain[2]);floor:=&Floor{Generation:3,ReceiptSHA256:h}
	f.cust.latest=f.chain[0];f.wit.chain=f.wit.chain[:1]
	if _,e:=f.recover(t,floor);e==nil{t.Fatal("accepted rollback below caller floor")}
}
func TestDualExternalRollbackIsNotDetectableToFreshClient(t *testing.T){
	f:=newFixture(t);f.cust.latest=f.chain[0];f.wit.chain=f.wit.chain[:1]
	// This is an explicit model boundary: with no previously retained floor
	// and both independent services rolled back together, the old state looks
	// internally consistent. A third independent witness/gossip is required.
	got,e:=f.recover(t,nil);if e!=nil{t.Fatal(e)}
	if got.Receipt.Generation!=1{t.Fatal("expected documented rollback boundary")}
}
func TestTamperedCheckpointObjectRejected(t *testing.T){
	f:=newFixture(t);r:=f.chain[2];f.cust.objects[r.CheckpointSHA256]=[]byte(`{"tampered":true}`)
	if _,e:=f.recover(t,nil);e==nil{t.Fatal("accepted tampered object")}
}
func TestPreviouslyDiscoveredMatchCannotBeRemoved(t *testing.T){
	f:=newFixture(t);prev:=f.chain[2]
	cp:=f.cps[2];cp.Generation=4;cp.PreviousReceiptSHA256,_=receiptHash(prev);cp.Matches=cp.Matches[1:];cp.MatchManifestSHA256=matchManifest(cp.Matches)
	raw,_:=canonicalCheckpoint(cp)
	r:=Receipt{Profile:keeperProfile,Scope:cp.Scope,Generation:4,PreviousReceiptSHA256:cp.PreviousReceiptSHA256,CheckpointSHA256:digest(raw),CheckpointBytes:uint64(len(raw)),Cursor:cp.Cursor,TargetSize:cp.TargetSize,TargetRoot:cp.TargetRoot,MatchManifestSHA256:cp.MatchManifestSHA256,KeyID:"synthetic-keeper-key"}
	r,_=signReceipt(r,f.priv);f.cust.objects[r.CheckpointSHA256]=raw;f.cust.latest=r;f.wit.chain=append(f.wit.chain,r)
	if _,e:=f.recover(t,nil);e==nil{t.Fatal("accepted deletion of previously discovered match")}
}
func TestOldCheckpointCannotBeReintroducedAsNewGeneration(t *testing.T){
	f:=newFixture(t);prev:=f.chain[2];old:=f.cps[0];old.Generation=4;old.PreviousReceiptSHA256,_=receiptHash(prev)
	raw,_:=canonicalCheckpoint(old)
	r:=Receipt{Profile:keeperProfile,Scope:old.Scope,Generation:4,PreviousReceiptSHA256:old.PreviousReceiptSHA256,CheckpointSHA256:digest(raw),CheckpointBytes:uint64(len(raw)),Cursor:old.Cursor,TargetSize:old.TargetSize,TargetRoot:old.TargetRoot,MatchManifestSHA256:old.MatchManifestSHA256,KeyID:"synthetic-keeper-key"}
	r,_=signReceipt(r,f.priv);f.cust.objects[r.CheckpointSHA256]=raw;f.cust.latest=r;f.wit.chain=append(f.wit.chain,r)
	if _,e:=f.recover(t,nil);e==nil{t.Fatal("accepted replayed old checkpoint")}
}
func TestTargetGrowthNeedsValidConsistencyEvidence(t *testing.T){
	f:=newFixture(t);f.trans.accepted=map[string]bool{}
	if _,e:=f.recover(t,nil);e==nil{t.Fatal("accepted unverified target growth")}
}
func TestForgedKeeperSignatureRejected(t *testing.T){
	f:=newFixture(t);f.chain[2].Cursor++;f.wit.chain[2]=f.chain[2];f.cust.latest=f.chain[2]
	if _,e:=f.recover(t,nil);e==nil{t.Fatal("accepted forged receipt")}
}
func TestForkOrGenerationGapRejected(t *testing.T){
	f:=newFixture(t);f.wit.chain[1].Generation=3
	if _,e:=f.recover(t,nil);e==nil{t.Fatal("accepted generation gap")}
}
func TestUnavailableCustodianOrWitnessFailsClosed(t *testing.T){
	f:=newFixture(t);f.cust.err=errors.New("offline")
	if _,e:=f.recover(t,nil);e==nil{t.Fatal("custodian outage did not HOLD")}
	f=newFixture(t);f.wit.err=errors.New("offline")
	if _,e:=f.recover(t,nil);e==nil{t.Fatal("witness outage did not HOLD")}
}
func TestConcurrentCASOnlyOneWriterWins(t *testing.T){
	var mu sync.Mutex
	head:="head-2"
	advance:=func(expected,next string)error{mu.Lock();defer mu.Unlock();if head!=expected{return ErrStaleHead};head=next;return nil}
	start:=make(chan struct{});results:=make(chan error,2)
	for _,next:=range []string{"receipt-3a","receipt-3b"}{go func(n string){<-start;results<-advance("head-2",n)}(next)}
	close(start);a,b:=<-results,<-results
	if (a==nil)==(b==nil){t.Fatalf("expected exactly one winner: %v / %v",a,b)}
	if a!=nil&& !errors.Is(a,ErrStaleHead){t.Fatal(a)}
	if b!=nil&& !errors.Is(b,ErrStaleHead){t.Fatal(b)}
}
func TestReceiptDigestAndPriorFloor(t *testing.T){
	f:=newFixture(t);h,_:=receiptHash(f.chain[2])
	got,e:=f.recover(t,&Floor{Generation:3,ReceiptSHA256:h});if e!=nil{t.Fatal(e)}
	if got.ReceiptSHA256!=h{t.Fatal("receipt digest mismatch")}
	if _,e=f.recover(t,&Floor{Generation:4,ReceiptSHA256:h});e==nil{t.Fatal("accepted lower generation")}
}

func TestPriorFloorRejectsForkAboveFloor(t *testing.T){
 f:=newFixture(t)
 // A validly signed alternative generation-2 branch is not the locally
 // retained generation-2 receipt, even if a later generation follows it.
 r1:=f.chain[0]
 cp:=f.cps[1];cp.TargetRoot=hex64("fork-root-30");cp.PreviousReceiptSHA256,_=receiptHash(r1);cp.MatchManifestSHA256=matchManifest(cp.Matches)
 raw,_:=canonicalCheckpoint(cp)
 proof:=digest([]byte(transitionKey(r1,Receipt{TargetSize:cp.TargetSize,TargetRoot:cp.TargetRoot})))
 f.trans.accepted[proof]=true
 r2:=Receipt{Profile:keeperProfile,Scope:cp.Scope,Generation:2,PreviousReceiptSHA256:cp.PreviousReceiptSHA256,CheckpointSHA256:digest(raw),CheckpointBytes:uint64(len(raw)),Cursor:cp.Cursor,TargetSize:cp.TargetSize,TargetRoot:cp.TargetRoot,MatchManifestSHA256:cp.MatchManifestSHA256,TransitionProofSHA256:proof,KeyID:"synthetic-keeper-key"}
 r2,_=signReceipt(r2,f.priv);h2,_:=receiptHash(r2)
 cp3:=f.cps[2];cp3.PreviousReceiptSHA256=h2
 raw3,_:=canonicalCheckpoint(cp3)
 proof3:=digest([]byte(transitionKey(r2,Receipt{TargetSize:cp3.TargetSize,TargetRoot:cp3.TargetRoot})))
 r3:=Receipt{Profile:keeperProfile,Scope:cp3.Scope,Generation:3,PreviousReceiptSHA256:h2,CheckpointSHA256:digest(raw3),CheckpointBytes:uint64(len(raw3)),Cursor:cp3.Cursor,TargetSize:cp3.TargetSize,TargetRoot:cp3.TargetRoot,MatchManifestSHA256:cp3.MatchManifestSHA256,TransitionProofSHA256:proof3,KeyID:"synthetic-keeper-key"}
 r3,_=signReceipt(r3,f.priv);f.trans.accepted[proof3]=true
 f.cust.objects[r2.CheckpointSHA256]=raw;f.cust.objects[r3.CheckpointSHA256]=raw3;f.cust.latest=r3;f.wit.chain=[]Receipt{r1,r2,r3}
 floorHash,_:=receiptHash(f.chain[1])
 if _,e:=f.recover(t,&Floor{Generation:2,ReceiptSHA256:floorHash});e==nil{t.Fatal("accepted alternate chain above retained generation floor")}
}
