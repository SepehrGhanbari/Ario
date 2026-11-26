package witness

import (
 "bytes"
 "crypto/ed25519"
 "encoding/json"
 "errors"
 "os"
 "os/exec"
 "path/filepath"
 "syscall"
 "testing"
)

func testKey()ed25519.PrivateKey{seed:=make([]byte,32);seed[0]=27;return ed25519.NewKeyFromSeed(seed)}
func config()Config{return Config{"synthetic-scope","synthetic-witness",1,testKey().Public().(ed25519.PublicKey),hash([]byte("genesis"))}}
func newStore(t *testing.T)Store{
 t.Helper();d:=t.TempDir();a,b:=filepath.Join(d,"local"),filepath.Join(d,"keeper")
 for _,p:=range []string{a,b}{if e:=os.Mkdir(p,0700);e!=nil{t.Fatal(e)}}
 s:=Store{filepath.Join(a,"state.json"),filepath.Join(b,"state.json"),config()}
 for _,p:=range []string{s.Local,s.Keeper}{if e:=durable(p,genesis(s.Config));e!=nil{t.Fatal(e)}}
 f,e:=os.OpenFile(s.Keeper+".lock",os.O_CREATE|os.O_EXCL|os.O_RDWR,0600);if e!=nil{t.Fatal(e)};f.Close()
 return s
}
func first(s Store,label string)Request{return Request{1,receiptHash(genesis(s.Config).Receipt),hash([]byte(label))}}
func next(r Receipt,label string)Request{return Request{r.Request.Generation+1,receiptHash(r),hash([]byte(label))}}
func advance(t *testing.T,s Store,r Request)Receipt{t.Helper();x,e:=s.Advance(r,testKey(),nil);if e!=nil{t.Fatal(e)};if !ed25519.Verify(s.Config.Public,signingBytes(x),x.Signature){t.Fatal("invalid receipt")};return x}
func expectHold(t *testing.T,s Store,r Request){
 t.Helper();calls:=0;x,e:=s.Advance(r,testKey(),func(string){calls++})
 if !errors.Is(e,ErrHold)||calls!=0||len(x.Signature)!=0{t.Fatalf("expected HOLD before reservation/signing, got %v, %d stages",e,calls)}
}
func readMust(t *testing.T,p string,c Config)State{t.Helper();v,e:=read(p,c);if e!=nil{t.Fatal(e)};return v}
func restore(t *testing.T,p string,v State){t.Helper();if e:=durable(p,v);e!=nil{t.Fatal(e)}}

func TestProgressAndExactRetry(t *testing.T){
 s:=newStore(t);a:=first(s,"A");r:=advance(t,s,a)
 count:=0;again,e:=s.Advance(a,testKey(),func(string){count++})
 if e!=nil||count!=0||!bytes.Equal(enc(r),enc(again)){t.Fatal("retry not exact")}
 expectHold(t,s,first(s,"fork"))
 expectHold(t,s,Request{3,receiptHash(r),hash([]byte("skip"))})
 q:=advance(t,s,next(r,"B"))
 if q.Request.Generation!=2{t.Fatal(q)}
 expectHold(t,s,a)
}
func TestLocalRollbackLossCorruptionAndKeeperLoss(t *testing.T){
 for _,name:=range []string{"local-rollback","local-delete","local-corrupt","keeper-rollback","keeper-delete","lock-delete","duplicate-json"}{t.Run(name,func(t *testing.T){
  s:=newStore(t);r:=advance(t,s,first(s,"A"))
  switch name{
  case "local-rollback":restore(t,s.Local,genesis(s.Config))
  case "keeper-rollback":restore(t,s.Keeper,genesis(s.Config))
  case "local-delete":if e:=os.Remove(s.Local);e!=nil{t.Fatal(e)}
  case "keeper-delete":if e:=os.Remove(s.Keeper);e!=nil{t.Fatal(e)}
  case "lock-delete":if e:=os.Remove(s.Keeper+".lock");e!=nil{t.Fatal(e)}
  case "local-corrupt":if e:=os.WriteFile(s.Local,[]byte("{}"),0600);e!=nil{t.Fatal(e)}
  case "duplicate-json":b:=enc(State{"COMMITTED",r});b=append(append([]byte{},b[:len(b)-1]...),[]byte(",\"Phase\":\"COMMITTED\"}")...);if e:=os.WriteFile(s.Local,b,0600);e!=nil{t.Fatal(e)}
  }
  expectHold(t,s,next(r,"B"))
 })}
}
func TestChangedKeyEpochIdentityCannotReuseHistory(t *testing.T){
 s:=newStore(t);r:=advance(t,s,first(s,"A"))
 for _,name:=range []string{"epoch","identity","scope","genesis","key"}{t.Run(name,func(t *testing.T){
  altered:=s;key:=testKey()
  switch name{case "epoch":altered.Config.Epoch++;case "identity":altered.Config.Identity="new";case "scope":altered.Config.Scope="new";case "genesis":altered.Config.GenesisRoot=hash([]byte("new"));case "key":seed:=make([]byte,32);seed[0]=28;key=ed25519.NewKeyFromSeed(seed);altered.Config.Public=key.Public().(ed25519.PublicKey)}
  calls:=0;_,e:=altered.Advance(next(r,"B"),key,func(string){calls++});if !errors.Is(e,ErrHold)||calls!=0{t.Fatal("accepted changed identity",e)}
 })}
}
// Process helper is only in the test binary; the deterministic test key
// is public and deliberately non-secret. SIGKILL is an actual process death.
func TestProcessHelper(t *testing.T){
 if os.Getenv("ARIO_R22_27_HELPER")!="1"{return}
 s:=Store{os.Getenv("ARIO_LOCAL"),os.Getenv("ARIO_KEEPER"),config()}
 var r Request;if json.Unmarshal([]byte(os.Getenv("ARIO_REQUEST")),&r)!=nil{os.Exit(3)}
 receipt,e:=s.Advance(r,testKey(),func(stage string){if stage==os.Getenv("ARIO_KILL_AT"){_ = syscall.Kill(os.Getpid(),syscall.SIGKILL);os.Exit(99)}})
 if e!=nil{os.Exit(2)}
 if _,e=os.Stdout.Write(enc(receipt));e!=nil{os.Exit(4)}
 os.Exit(0)
}
func command(t *testing.T,s Store,r Request,stage string)*exec.Cmd{
 t.Helper();exe,e:=os.Executable();if e!=nil{t.Fatal(e)}
 c:=exec.Command(exe,"-test.run=^TestProcessHelper$")
 c.Env=append(os.Environ(),"ARIO_R22_27_HELPER=1","ARIO_LOCAL="+s.Local,"ARIO_KEEPER="+s.Keeper,"ARIO_REQUEST="+string(enc(r)),"ARIO_KILL_AT="+stage)
 return c
}
func TestActualProcessKillAtFourBoundaries(t *testing.T){
 for _,stage:=range []string{"after-reserve","after-sign","after-keeper-commit","after-local-commit"}{t.Run(stage,func(t *testing.T){
  s:=newStore(t);req:=first(s,"A")
  out,e:=command(t,s,req,stage).Output();var x *exec.ExitError
  if !errors.As(e,&x)||!x.Sys().(syscall.WaitStatus).Signaled()||x.Sys().(syscall.WaitStatus).Signal()!=syscall.SIGKILL||len(out)!=0{t.Fatalf("not killed before release: %v %q",e,out)}
  rem:=readMust(t,s.Keeper,s.Config);loc:=readMust(t,s.Local,s.Config)
  switch stage{
  case "after-reserve","after-sign":
   if rem.Phase!="RESERVED"||len(rem.Receipt.Signature)!=0||loc.Receipt.Request.Generation!=0{t.Fatal("reservation state")}
   expectHold(t,s,req);expectHold(t,s,first(s,"fork"))
  case "after-keeper-commit":
   if rem.Phase!="COMMITTED"||rem.Receipt.Request.Generation!=1||loc.Receipt.Request.Generation!=0{t.Fatal("partial commit")}
   expectHold(t,s,req);expectHold(t,s,first(s,"fork"))
  case "after-local-commit":
   if !bytes.Equal(enc(rem),enc(loc)){t.Fatal("lost response state")}
   // Restart in a new OS process and return exact committed receipt.
   raw,e:=command(t,s,req,"").Output();if e!=nil||!bytes.Equal(raw,enc(rem.Receipt)){t.Fatalf("retry mismatch %v",e)}
   expectHold(t,s,first(s,"fork"))
  }
 })}
}
func TestConcurrentProcessesOnlyOneConflictingProposalWins(t *testing.T){
 s:=newStore(t)
 a,b:=command(t,s,first(s,"A"),""),command(t,s,first(s,"B"),"")
 var aa,bb bytes.Buffer;a.Stdout=&aa;b.Stdout=&bb
 if e:=a.Start();e!=nil{t.Fatal(e)};if e:=b.Start();e!=nil{_ = a.Process.Kill();_ = a.Wait();t.Fatal(e)}
 ea,eb:=a.Wait(),b.Wait()
 if (ea==nil)==(eb==nil){t.Fatalf("expected one winner: %v %v",ea,eb)}
 winner,loser:=aa.Bytes(),bb.Bytes();failure:=eb;if ea!=nil{winner,loser=loser,winner;failure=ea}
 var x *exec.ExitError;if !errors.As(failure,&x)||x.ExitCode()!=2||len(loser)!=0{t.Fatal("loser released bytes")}
 remote:=readMust(t,s.Keeper,s.Config);local:=readMust(t,s.Local,s.Config)
 if !bytes.Equal(winner,enc(remote.Receipt))||!bytes.Equal(enc(remote),enc(local)){t.Fatal("durable winner mismatch")}
}
func TestJointRollbackWithSameKeyExplicitBoundary(t *testing.T){
 s:=newStore(t);r:=advance(t,s,first(s,"A"))
 // Both same-admin stores restored; old key still usable. This is RED,
 // not security success: two conflicting signatures at the same generation.
 restore(t,s.Local,genesis(s.Config));restore(t,s.Keeper,genesis(s.Config))
 fork:=advance(t,s,first(s,"B"))
 if r.Request.Generation!=fork.Request.Generation||r.Request.Root==fork.Request.Root||!ed25519.Verify(s.Config.Public,signingBytes(r),r.Signature){t.Fatal("counterexample not reproduced")}
}
func TestExportableKeyBypassesGuardExplicitBoundary(t *testing.T){
 s:=newStore(t);r:=advance(t,s,first(s,"A"))
 if e:=os.Remove(s.Local);e!=nil{t.Fatal(e)};expectHold(t,s,first(s,"B"))
 // Same test key can sign outside Advance; signature verification alone
 // cannot prove that the monotonic keeper was consulted.
 fork:=Receipt{profile,configHash(s.Config),first(s,"B"),nil}
 fork.Signature=ed25519.Sign(testKey(),signingBytes(fork))
 if r.Request.Generation!=fork.Request.Generation||r.Request.Root==fork.Request.Root||!ed25519.Verify(s.Config.Public,signingBytes(fork),fork.Signature){t.Fatal("bypass not reproduced")}
}
