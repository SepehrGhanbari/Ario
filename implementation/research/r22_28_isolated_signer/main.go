// R22.28 Linux two-UID synthetic signing boundary. Not production.
package main
import("bytes";"crypto/ed25519";"crypto/rand";"crypto/sha256";"encoding/hex";"encoding/json";"errors";"fmt";"io";"net";"os";"path/filepath";"strconv";"syscall";"time")
const profile="ARIO-R22.28-SYNTHETIC-v1"
type Request struct{ Generation uint64; Previous,Root string }
type Receipt struct{ Profile,Public string; Request Request; Signature []byte }
type State struct{ Phase string; Receipt Receipt }
type Reply struct{ Status string; Receipt *Receipt }
func enc(v any)[]byte{b,e:=json.Marshal(v);if e!=nil{panic(e)};return b}
func hash(b []byte)string{h:=sha256.Sum256(b);return hex.EncodeToString(h[:])}
func valid(s string)bool{b,e:=hex.DecodeString(s);return e==nil&&len(b)==32&&hex.EncodeToString(b)==s}
func signbytes(r Receipt)[]byte{r.Signature=nil;return enc(r)}
func strict(b []byte,v any)error{d:=json.NewDecoder(bytes.NewReader(b));d.DisallowUnknownFields();if e:=d.Decode(v);e!=nil{return e};if !bytes.Equal(b,enc(v)){return errors.New("noncanonical")};return nil}
func durable(path string,b []byte)error{d:=filepath.Dir(path);f,e:=os.CreateTemp(d,".state-");if e!=nil{return e};defer os.Remove(f.Name());defer f.Close();n,e:=f.Write(b);if e!=nil{return e};if n!=len(b){return io.ErrShortWrite};if e=f.Sync();e!=nil{return e};if e=f.Close();e!=nil{return e};if e=os.Rename(f.Name(),path);e!=nil{return e};p,e:=os.Open(d);if e!=nil{return e};defer p.Close();return p.Sync()}
func initial(pub string)State{return State{"COMMITTED",Receipt{profile,pub,Request{0,hash(nil),hash([]byte("synthetic genesis"))},nil}}}
func provision(dir string)error{
 // Never overwrite an existing identity. Test-only provisioning.
 f,e:=os.OpenFile(filepath.Join(dir,"identity.lock"),os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600);if e!=nil{return e};if e=f.Close();e!=nil{return e}
 pub,key,e:=ed25519.GenerateKey(rand.Reader);if e!=nil{return e}
 if e=durable(filepath.Join(dir,"key"),key);e!=nil{return e}
 s:=initial(hex.EncodeToString(pub));if e=durable(filepath.Join(dir,"state"),enc(s));e!=nil{return e}
 fmt.Println(string(enc(s.Receipt)));return nil
}
func advance(dir string,key ed25519.PrivateKey,q Request)(*Receipt,error){
 pub:=key.Public().(ed25519.PublicKey);p:=hex.EncodeToString(pub)
 if q.Generation==0||!valid(q.Previous)||!valid(q.Root){return nil,errors.New("schema")}
 raw,e:=os.ReadFile(filepath.Join(dir,"state"));if e!=nil||len(raw)>8192{return nil,errors.New("missing or oversized state")}
 var s State;if e=strict(raw,&s);e!=nil||s.Phase!="COMMITTED"||s.Receipt.Profile!=profile||s.Receipt.Public!=p{return nil,errors.New("state invalid")}
 r:=s.Receipt
 if r.Request.Generation==0 {if !bytes.Equal(enc(s),enc(initial(p))){return nil,errors.New("genesis")}}else if !valid(r.Request.Previous)||!valid(r.Request.Root)||!ed25519.Verify(pub,signbytes(r),r.Signature){return nil,errors.New("invalid receipt")}
 if q==r.Request&&r.Request.Generation>0{return &r,nil}
 if r.Request.Generation==^uint64(0)||q.Generation!=r.Request.Generation+1||q.Previous!=hash(enc(r)){return nil,errors.New("floor mismatch")}
 n:=Receipt{profile,p,q,nil}
 if e=durable(filepath.Join(dir,"state"),enc(State{"RESERVED",n}));e!=nil{return nil,e}
 n.Signature=ed25519.Sign(key,signbytes(n));fmt.Fprintln(os.Stderr,"SIGN")
 if e=durable(filepath.Join(dir,"state"),enc(State{"COMMITTED",n}));e!=nil{return nil,e}
 return &n,nil
}
func peer(c *net.UnixConn)(uint32,error){raw,e:=c.SyscallConn();if e!=nil{return 0,e};var u *syscall.Ucred;var inner error;e=raw.Control(func(fd uintptr){u,inner=syscall.GetsockoptUcred(int(fd),syscall.SOL_SOCKET,syscall.SO_PEERCRED)});if e!=nil{return 0,e};if inner!=nil{return 0,inner};return u.Uid,nil}
func handle(c *net.UnixConn,uid uint32,dir string,key ed25519.PrivateKey){
 defer c.Close();c.SetDeadline(time.Now().Add(2*time.Second))
 answer:=Reply{"HOLD",nil}
 // Read at most 8193 bytes with the existing deadline, even for an
 // unauthorized peer, so a well-framed request gets a deterministic HOLD.
 // No parse, state access or signature operation precedes peer authorization.
 u,peerErr:=peer(c)
 b,readErr:=io.ReadAll(io.LimitReader(c,8193))
 if peerErr==nil&&u==uid&&readErr==nil&&len(b)<=8192{
  var q Request
  if strict(b,&q)==nil{if r,e:=advance(dir,key,q);e==nil{answer=Reply{"SIGNED_TEST_ONLY",r}}}
 }
 _,_=c.Write(enc(answer))
}
func serve(dir,socket string,uid uint32)error{
 // Lock is under signer-only permissions. No concurrent signer instances.
 f,e:=os.OpenFile(filepath.Join(dir,"identity.lock"),os.O_RDWR,0);if e!=nil{return e};defer f.Close()
 if e=syscall.Flock(int(f.Fd()),syscall.LOCK_EX|syscall.LOCK_NB);e!=nil{return e}
 key,e:=os.ReadFile(filepath.Join(dir,"key"));if e!=nil||len(key)!=ed25519.PrivateKeySize{return errors.New("key missing")}
 // Only the signer-owned socket directory may be used. No publisher writes.
 if e=os.Remove(socket);e!=nil&&!os.IsNotExist(e){return e}
 l,e:=net.ListenUnix("unix",&net.UnixAddr{Name:socket,Net:"unix"});if e!=nil{return e};defer l.Close()
 if e=os.Chmod(socket,0666);e!=nil{return e}
 for{c,e:=l.AcceptUnix();if e!=nil{return e};handle(c,uid,dir,ed25519.PrivateKey(key))}
}
func verify(path string)error{b,e:=os.ReadFile(path);if e!=nil{return e};var r Receipt;if e=strict(b,&r);e!=nil{return e};p,e:=hex.DecodeString(r.Public);if e!=nil||len(p)!=32||r.Profile!=profile||!ed25519.Verify(ed25519.PublicKey(p),signbytes(r),r.Signature){return errors.New("bad signature")};return nil}
func main(){var e error;switch{
case len(os.Args)==3&&os.Args[1]=="init":e=provision(os.Args[2])
case len(os.Args)==5&&os.Args[1]=="serve":var u uint64;u,e=strconv.ParseUint(os.Args[4],10,32);if e==nil{e=serve(os.Args[2],os.Args[3],uint32(u))}
case len(os.Args)==3&&os.Args[1]=="verify":e=verify(os.Args[2])
default:e=errors.New("usage: init dir | serve dir socket uid | verify receipt")
};if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(1)}}
