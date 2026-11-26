// Research-only first-generation adapter: reuse R22.27 Store.Advance and R22.26 Read.
package main
import (
 "bytes";"crypto/ed25519";"crypto/rand";"crypto/sha256";"encoding/hex";"encoding/json";"fmt";"io";"os";"path/filepath"
 q "ario-r22-26-quorum-gossip"
 w "ario-r22-27-durable-witness"
)
const profile="ARIO-R22.27-WITNESS-v1"
const zero="0000000000000000000000000000000000000000000000000000000000000000"
type Pins struct { Policy q.Policy; Genesis string }
type Proof struct { ID string; Receipt w.Receipt; Reply q.Reply }
func enc(x any) []byte {b,e:=json.Marshal(x);if e!=nil {panic(e)};return b}
func digest(x any) string {b:=sha256.Sum256(enc(x));return hex.EncodeToString(b[:])}
func check(e error) {if e!=nil {fmt.Fprintln(os.Stderr,e);os.Exit(1)}}
func fail(s string) {check(fmt.Errorf("HOLD: %s",s))}
func read(path string) []byte {f,e:=os.Open(path);check(e);defer f.Close();b,e:=io.ReadAll(io.LimitReader(f,(2<<20)+1));check(e);if len(b)>2<<20 {fail("size")};return b}
func decode(b []byte,v any) {d:=json.NewDecoder(bytes.NewReader(b));d.DisallowUnknownFields();check(d.Decode(v));if d.Decode(new(any))!=io.EOF {fail("trailing JSON")}}
func write(path string,b []byte) {f,e:=os.OpenFile(path,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600);check(e);n,e:=f.Write(b);check(e);if n!=len(b){fail("short write")};check(f.Sync());check(f.Close())}
func genesis(c w.Config) w.Receipt {return w.Receipt{Profile:profile,ConfigHash:digest(c),Request:w.Request{Generation:0,Previous:zero,Root:c.GenesisRoot}}}
func config(p Pins,m q.Member) w.Config {return w.Config{Scope:p.Policy.Scope,Identity:m.ID,Epoch:p.Policy.Epoch,Public:m.Key,GenesisRoot:p.Genesis}}
func validhash(s string) bool {b,e:=hex.DecodeString(s);return e==nil&&len(b)==32&&hex.EncodeToString(b)==s}
func validatePins(p Pins) {
 if !validhash(p.Genesis)||p.Policy.Scope!="ario-r2230-test"||p.Policy.Epoch!=1||p.Policy.Threshold!=3||len(p.Policy.Members)!=3 {fail("policy")}
 ids,domains,keys:=map[string]bool{},map[string]bool{},map[string]bool{}
 for _,m:=range p.Policy.Members {k:=hex.EncodeToString(m.Key);if m.ID==""||m.Domain==""||len(m.Key)!=32||ids[m.ID]||domains[m.Domain]||keys[k]{fail("duplicate or invalid pin")};ids[m.ID]=true;domains[m.Domain]=true;keys[k]=true}
}
func main() {
 a:=os.Args
 if len(a)==5&&a[1]=="init" {
  dir,id,gen:=a[2],a[3],a[4];if !validhash(gen){fail("genesis")}
  pub,key,e:=ed25519.GenerateKey(rand.Reader);check(e)
  c:=w.Config{Scope:"ario-r2230-test",Identity:id,Epoch:1,Public:pub,GenesisRoot:gen}
  write(filepath.Join(dir,"key"),key);write(filepath.Join(dir,"config"),enc(c))
  initial:=enc(w.State{Phase:"COMMITTED",Receipt:genesis(c)})
  write(filepath.Join(dir,"local"),initial);write(filepath.Join(dir,"keeper"),initial);write(filepath.Join(dir,"keeper.lock"),nil)
  d,e:=os.Open(dir);check(e);check(d.Sync());check(d.Close())
  fmt.Println(string(enc(q.Member{ID:id,Domain:id,Key:pub})));return
 }
 if len(a)==6&&a[1]=="reserve" {
  dir,pinfile,nonce,root:=a[2],a[3],a[4],a[5]
  var p Pins;decode(read(pinfile),&p);validatePins(p)
  var c w.Config;decode(read(filepath.Join(dir,"config")),&c)
  var member *q.Member
  for i:=range p.Policy.Members {if p.Policy.Members[i].ID==c.Identity {member=&p.Policy.Members[i]}}
  if member==nil||!bytes.Equal(enc(config(p,*member)),enc(c))||!validhash(root)||!validhash(nonce){fail("pin")}
  key:=ed25519.PrivateKey(read(filepath.Join(dir,"key")))
  req:=w.Request{Generation:1,Previous:digest(genesis(c)),Root:root}
  store:=w.Store{Local:filepath.Join(dir,"local"),Keeper:filepath.Join(dir,"keeper"),Config:c}
  receipt,e:=store.Advance(req,key,nil);check(e)
  st:=q.Statement{Profile:"ARIO-R22.26-READ-v1",Scope:p.Policy.Scope,PolicyHash:digest(p.Policy),Nonce:nonce,Epoch:p.Policy.Epoch,History:[]string{root}}
  fmt.Println(string(enc(Proof{ID:c.Identity,Receipt:receipt,Reply:q.Reply{ID:c.Identity,Statement:st,Signature:ed25519.Sign(key,enc(st))}})));return
 }
 if len(a)==5&&a[1]=="verify" {
  var p Pins;decode(read(a[2]),&p);validatePins(p);nonce,root:=a[3],a[4]
  if !validhash(root)||!validhash(nonce){fail("binding")}
  raw,e:=io.ReadAll(io.LimitReader(os.Stdin,(2<<20)+1));check(e);if len(raw)>2<<20 {fail("size")}
  var proofs []Proof;decode(raw,&proofs)
  if len(proofs)!=3 {fail("write reservations")}
  seen:=map[string]bool{};replies:=[]q.Reply{}
  for _,proof:=range proofs {
   var m *q.Member;for i:=range p.Policy.Members {if p.Policy.Members[i].ID==proof.ID {m=&p.Policy.Members[i]}}
   if m==nil||seen[proof.ID]||proof.Reply.ID!=proof.ID {fail("member")};seen[proof.ID]=true
   c:=config(p,*m);r:=proof.Receipt;sig:=r.Signature;r.Signature=nil
   if r.Profile!=profile||r.ConfigHash!=digest(c)||r.Request!=(w.Request{Generation:1,Previous:digest(genesis(c)),Root:root})||!ed25519.Verify(m.Key,enc(r),sig) {fail("receipt")}
   if len(proof.Reply.Statement.History)!=1||proof.Reply.Statement.History[0]!=root {fail("root")}
   replies=append(replies,proof.Reply)
  }
  result:=q.Read(p.Policy,nonce,replies,nil)
  if result.Status!="REVIEWABLE_ONLY"||result.Evidence!=3||result.Floor.Generation!=1 {fail("quorum")}
  fmt.Println("RESERVATIONS_VERIFIED_TEST_ONLY");return
 }
 fail("usage")
}
