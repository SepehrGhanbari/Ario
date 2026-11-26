// Linux research model: durable witness state and a simulated external floor.
// No actual independent administrator, key isolation, or production signer.
package witness

import (
 "bytes"
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "os"
 "path/filepath"
 "syscall"
)

const profile="ARIO-R22.27-WITNESS-v1"
const zero="0000000000000000000000000000000000000000000000000000000000000000"
const maxState=16384
var ErrHold=errors.New("HOLD")
type Config struct{Scope,Identity string;Epoch uint64;Public ed25519.PublicKey;GenesisRoot string}
type Request struct{Generation uint64;Previous,Root string}
type Receipt struct{Profile,ConfigHash string;Request Request;Signature []byte}
type State struct{Phase string;Receipt Receipt}
type Store struct{Local,Keeper string;Config Config}
type hook func(string)

func hash(b []byte)string{h:=sha256.Sum256(b);return hex.EncodeToString(h[:])}
func enc(x any)[]byte{b,e:=json.Marshal(x);if e!=nil{panic(e)};return b}
func validHash(s string)bool{b,e:=hex.DecodeString(s);return e==nil&&len(b)==32&&hex.EncodeToString(b)==s}
func validConfig(c Config)bool{return c.Scope!=""&&c.Identity!=""&&c.Epoch>0&&len(c.Public)==ed25519.PublicKeySize&&validHash(c.GenesisRoot)}
func configHash(c Config)string{return hash(enc(c))}
func receiptHash(r Receipt)string{return hash(enc(r))}
func signingBytes(r Receipt)[]byte{r.Signature=nil;return enc(r)}
func genesis(c Config)State{return State{"COMMITTED",Receipt{profile,configHash(c),Request{0,zero,c.GenesisRoot},nil}}}
func fail(s string)error{return fmt.Errorf("%w: %s",ErrHold,s)}
func validate(s State,c Config)error{
 r:=s.Receipt
 if !validConfig(c)||r.Profile!=profile||r.ConfigHash!=configHash(c)||!validHash(r.Request.Previous)||!validHash(r.Request.Root){return fail("state identity or schema")}
 if r.Request.Generation==0{if !bytes.Equal(enc(s),enc(genesis(c))){return fail("genesis mismatch")};return nil}
 if s.Phase=="RESERVED"&&r.Signature==nil{return nil}
 if s.Phase!="COMMITTED"||len(r.Signature)!=ed25519.SignatureSize||!ed25519.Verify(c.Public,signingBytes(r),r.Signature){return fail("state phase or signature")}
 return nil
}
func read(path string,c Config)(State,error){
 var s State
 f,e:=os.Open(path);if e!=nil{return s,fail("state missing or unreadable")};defer f.Close()
 raw,e:=io.ReadAll(io.LimitReader(f,maxState+1));if e!=nil||len(raw)>maxState{return s,fail("state size or read")}
 d:=json.NewDecoder(bytes.NewReader(raw));d.DisallowUnknownFields()
 if e=d.Decode(&s);e!=nil||!bytes.Equal(raw,enc(s)){return State{},fail("noncanonical state")}
 if e=validate(s,c);e!=nil{return State{},e};return s,nil
}
// Atomic replacement on a local Linux filesystem; directory fsync is required.
// Any error means no successful signing response, even if a rename happened.
func durable(path string,s State)error{
 dir:=filepath.Dir(path);f,e:=os.CreateTemp(dir,".witness-");if e!=nil{return e}
 defer os.Remove(f.Name());defer f.Close()
 b:=enc(s);n,e:=f.Write(b);if e!=nil{return e};if n!=len(b){return io.ErrShortWrite}
 if e=f.Sync();e!=nil{return e};if e=f.Close();e!=nil{return e}
 if e=os.Rename(f.Name(),path);e!=nil{return e}
 d,e:=os.Open(dir);if e!=nil{return e};defer d.Close();return d.Sync()
}
func (s Store) Advance(req Request,key ed25519.PrivateKey,point hook)(Receipt,error){
 var none Receipt
 if !validConfig(s.Config)||len(key)!=ed25519.PrivateKeySize||!bytes.Equal(key.Public().(ed25519.PublicKey),s.Config.Public){return none,fail("pinned key mismatch")}
 if req.Generation==0||!validHash(req.Previous)||!validHash(req.Root){return none,fail("request schema")}
 // Keeper's stable lock is a test stand-in for an atomic external CAS.
 // It is never created by the signer; loss of that file is HOLD.
 lock,e:=os.OpenFile(s.Keeper+".lock",os.O_RDWR,0);if e!=nil{return none,fail("keeper lock missing")};defer lock.Close()
 if e=syscall.Flock(int(lock.Fd()),syscall.LOCK_EX);e!=nil{return none,e};defer syscall.Flock(int(lock.Fd()),syscall.LOCK_UN)
 remote,e:=read(s.Keeper,s.Config);if e!=nil{return none,e}
 local,e:=read(s.Local,s.Config);if e!=nil{return none,e}
 if remote.Phase!="COMMITTED"||local.Phase!="COMMITTED"||!bytes.Equal(enc(remote),enc(local)){return none,fail("pending transaction or local history differs from keeper")}
 r:=remote.Receipt
 if req==r.Request&&req.Generation>0{return r,nil} // lost response: exact stored receipt, no signing
 if r.Request.Generation==^uint64(0)||req.Generation!=r.Request.Generation+1||req.Previous!=receiptHash(r){return none,fail("stale, skipped or conflicting generation")}
 next:=Receipt{profile,configHash(s.Config),req,nil}
 if e=durable(s.Keeper,State{"RESERVED",next});e!=nil{return none,e}
 if point!=nil{point("after-reserve")}
 next.Signature=ed25519.Sign(key,signingBytes(next))
 if point!=nil{point("after-sign")}
 committed:=State{"COMMITTED",next}
 if e=durable(s.Keeper,committed);e!=nil{return none,e}
 if point!=nil{point("after-keeper-commit")}
 if e=durable(s.Local,committed);e!=nil{return none,e}
 if point!=nil{point("after-local-commit")}
 return next,nil
}
