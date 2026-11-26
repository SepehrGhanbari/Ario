package main

import (
 "bytes"
 "context"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "fmt"
 "io"
 "log"
 "net/http"
 "os"
 "path/filepath"
 "strings"
 "sync"
 "time"

 "sigsum.org/sigsum-go/pkg/client"
 "sigsum.org/sigsum-go/pkg/crypto"
 "sigsum.org/sigsum-go/pkg/policy"
 "sigsum.org/sigsum-go/pkg/requests"
 "sigsum.org/sigsum-go/pkg/types"
)

const logURL = "https://test.sigsum.org/barreleye"
const logKeyHashHex = "4e89cc51651f0d95f3c6127c15e1a42e3ddf7046c5b17b752689c402e773bb4d"
const signerPublicHex = "3e969aa93418174683d6524f98ad908ddcf3316f5eda7fb555f647f002d0fb5e"
const policyText = "log 4644af2abd40f4895a003bca350f9d5912ab301a49c77f13e5b6d905c20a5fe6 https://test.sigsum.org/barreleye\n" +
 "witness poc.sigsum.org/nisse 1c25f8a44c635457e2e391d1efbca7d4c2951a0aef06225a881e46b98962ac6c\n" +
 "witness rgdd.se/poc-witness 28c92a5a3a054d317c86fc2eeb6a7ab2054d6217100d0be67ded5b74323c5806\n" +
 "witness witness1.smartit.nu/witness1 f4855a0f46e8a3e23bb40faf260ee57ab8a18249fa402f2ca2d28a60e1a3130e\n" +
 "group quorum-rule 2 poc.sigsum.org/nisse rgdd.se/poc-witness witness1.smartit.nu/witness1\n" +
 "quorum quorum-rule\n"

const floorA uint64 = 281653
const floorARoot = "19530988e672bb6290bf5d70e361c062d2dd990699c978a06acf1b2eff83f2af"
const floorB uint64 = 281670
const floorBRoot = "dafc6911b16d150b1628937dd5030ba1b188b6ffe916837d41db37e4b867cefc"
const firstIndex uint64 = 281650
var expectedChecksums = []string{
 "23eb0a5f1affd64579629fe67e6fe69e1b26c6837e5638421a88359869c273d4",
 "3a70faa045ea6a085e41dae89f75d2209204248d2d1214707c998b296d61e38a",
 "9d782dd4bd165e76ba85a4df8d36cc3c9011c3623e435d967d6e80571b24646f",
}

type responseRecord struct { URL string; Status int; Body []byte }
type captureTransport struct { base http.RoundTripper; mu sync.Mutex; records []responseRecord }

func (t *captureTransport) RoundTrip(req *http.Request) (*http.Response, error) {
 resp, err := t.base.RoundTrip(req)
 if err != nil { return nil, err }
 body, err := io.ReadAll(resp.Body)
 if err != nil { resp.Body.Close(); return nil, err }
 resp.Body.Close()
 resp.Body = io.NopCloser(bytes.NewReader(body))
 t.mu.Lock()
 t.records = append(t.records, responseRecord{URL:req.URL.String(), Status:resp.StatusCode, Body:append([]byte(nil), body...)})
 t.mu.Unlock()
 return resp, nil
}
func (t *captureTransport) last(want string) (responseRecord, error) {
 t.mu.Lock(); defer t.mu.Unlock()
 if len(t.records)==0 { return responseRecord{}, fmt.Errorf("HOLD_NO_CAPTURED_RESPONSE") }
 r:=t.records[len(t.records)-1]
 if r.Status!=http.StatusOK || !strings.Contains(r.URL,want) || len(r.Body)==0 || len(r.Body)>1<<20 {
  return responseRecord{}, fmt.Errorf("HOLD_BAD_RESPONSE want=%s status=%d url=%s bytes=%d",want,r.Status,r.URL,len(r.Body))
 }
 return r,nil
}

type floorPin struct { Size uint64 `json:"size"`; Root string `json:"root"`; ProofFile string `json:"proof_file"` }
type leafPin struct { Index uint64 `json:"index"`; Checksum string `json:"checksum"`; LeafFile string `json:"leaf_file"`; InclusionFile string `json:"inclusion_file"` }
type manifest struct {
 Schema string `json:"schema"`
 CapturedAtUTC string `json:"captured_at_utc"`
 RunnerClockAttested bool `json:"runner_clock_attested"`
 LogURL string `json:"log_url"`
 CheckpointURL string `json:"checkpoint_url"`
 CheckpointHTTPStatus int `json:"checkpoint_http_status"`
 TreeSize uint64 `json:"tree_size"`
 RootHash string `json:"root_hash"`
 CosignatureCount int `json:"cosignature_count"`
 Floors []floorPin `json:"floors"`
 Leaves []leafPin `json:"leaves"`
 Files map[string]string `json:"files"`
 Publication string `json:"publication"`
 Signing string `json:"signing"`
 Freshness string `json:"freshness"`
 GlobalLatest string `json:"global_latest"`
 IndependentCustody string `json:"independent_custody"`
 TrustActivation string `json:"trust_activation"`
 Production string `json:"production"`
}

func parseHash(s string) (crypto.Hash,error) {
 var h crypto.Hash
 b,err:=hex.DecodeString(s)
 if err!=nil || len(b)!=32 { return h,fmt.Errorf("HOLD_BAD_HASH") }
 copy(h[:],b); return h,nil
}
func mustHash(s string) crypto.Hash { h,e:=parseHash(s); if e!=nil { log.Fatal(e) }; return h }
func digest(b []byte) string { h:=sha256.Sum256(b); return hex.EncodeToString(h[:]) }
func writeFile(root,name string,b []byte) error {
 p:=filepath.Join(root,name)
 if err:=os.MkdirAll(filepath.Dir(p),0755); err!=nil{return err}
 return os.WriteFile(p,b,0644)
}
func readFile(root,name string)([]byte,error){return os.ReadFile(filepath.Join(root,name))}
func fileHashes(root string,names []string)(map[string]string,error){
 out:=map[string]string{}
 for _,n:=range names { b,e:=readFile(root,n); if e!=nil{return nil,e}; out[n]=digest(b) }
 return out,nil
}
func loadPolicy() *policy.Policy {
 p,err:=policy.ParseConfig(strings.NewReader(policyText)); if err!=nil {log.Fatal(err)}; return p
}
func signer() (crypto.PublicKey,crypto.Hash) {
 var pub crypto.PublicKey
 b,err:=hex.DecodeString(signerPublicHex); if err!=nil || len(b)!=32 {log.Fatal("HOLD_SIGNER_PIN")}
 copy(pub[:],b)
 return pub,crypto.Hash(sha256.Sum256(pub[:]))
}
func checkFloor(head types.TreeHead, floor floorPin) error {
 root,err:=parseHash(floor.Root); if err!=nil{return err}
 if head.Size<floor.Size {return fmt.Errorf("HOLD_STALE_CHECKPOINT")}
 if head.Size==floor.Size && head.RootHash!=root {return fmt.Errorf("HOLD_SAME_SIZE_CONFLICT")}
 return nil
}
func capture(out string) error {
 if _,err:=os.Stat(out); err==nil {return fmt.Errorf("HOLD_OUTPUT_EXISTS")}
 if err:=os.MkdirAll(out,0755); err!=nil{return err}
 tap:=&captureTransport{base:http.DefaultTransport}
 hc:=&http.Client{Transport:tap,Timeout:20*time.Second,CheckRedirect:func(*http.Request,[]*http.Request)error{return fmt.Errorf("HOLD_REDIRECT_DENIED")}}
 cli:=client.New(client.Config{URL:logURL,HTTPClient:hc})
 ctx,cancel:=context.WithTimeout(context.Background(),180*time.Second); defer cancel()
 cth,err:=cli.GetTreeHead(ctx); if err!=nil{return err}
 headResp,err:=tap.last("get-tree-head"); if err!=nil{return err}
 if err:=writeFile(out,"checkpoint.raw",headResp.Body); err!=nil{return err}
 var parsed types.CosignedTreeHead
 if err:=parsed.FromASCII(bytes.NewReader(headResp.Body)); err!=nil{return fmt.Errorf("HOLD_CHECKPOINT_PARSE: %w",err)}
 cth=parsed
 p:=loadPolicy()
 logKH:=mustHash(logKeyHashHex)
 if err:=p.VerifyCosignedTreeHead(&logKH,&cth); err!=nil{return fmt.Errorf("HOLD_CHECKPOINT_SIGNATURES: %w",err)}
 if len(cth.Cosignatures)<2 {return fmt.Errorf("HOLD_WITNESS_QUORUM")}
 if cth.Size<=floorB {return fmt.Errorf("HOLD_HEAD_NOT_NEWER_THAN_RETAINED_FLOOR")}
 if err:=checkFloor(cth.TreeHead,floorPin{Size:floorA,Root:floorARoot}); err!=nil{return err}
 if err:=checkFloor(cth.TreeHead,floorPin{Size:floorB,Root:floorBRoot}); err!=nil{return err}
 var canonical bytes.Buffer
 if err:=cth.ToASCII(&canonical); err!=nil{return err}
 if err:=writeFile(out,"checkpoint.canonical",canonical.Bytes()); err!=nil{return err}
 floors:=[]floorPin{{Size:floorA,Root:floorARoot,ProofFile:"consistency-281653.raw"},{Size:floorB,Root:floorBRoot,ProofFile:"consistency-281670.raw"}}
 for _,f:=range floors {
  oldRoot,_:=parseHash(f.Root); old:=types.TreeHead{Size:f.Size,RootHash:oldRoot}
  proof,err:=cli.GetConsistencyProof(ctx,requests.ConsistencyProof{OldSize:f.Size,NewSize:cth.Size}); if err!=nil{return err}
  rec,err:=tap.last("get-consistency-proof"); if err!=nil{return err}
  if err:=proof.Verify(&old,&cth.TreeHead); err!=nil{return fmt.Errorf("HOLD_CONSISTENCY_%d: %w",f.Size,err)}
  if err:=writeFile(out,f.ProofFile,rec.Body); err!=nil{return err}
 }
 pub,signerHash:=signer()
 leaves,err:=cli.GetLeaves(ctx,requests.Leaves{StartIndex:firstIndex,EndIndex:firstIndex+uint64(len(expectedChecksums))}); if err!=nil{return err}
 leavesResp,err:=tap.last("get-leaves"); if err!=nil{return err}
 if err:=writeFile(out,"leaves.raw",leavesResp.Body); err!=nil{return err}
 if len(leaves)!=len(expectedChecksums){return fmt.Errorf("HOLD_LEAF_COUNT")}
 leafPins:=[]leafPin{}
 for i,leaf:=range leaves {
  index:=firstIndex+uint64(i); checksum:=hex.EncodeToString(leaf.Checksum[:])
  if checksum!=expectedChecksums[i] || leaf.KeyHash!=signerHash || !leaf.Verify(&pub) {return fmt.Errorf("HOLD_LEAF_PIN_OR_SIGNATURE_%d",index)}
  var leafBuf bytes.Buffer
  if err:=leaf.ToASCII(&leafBuf); err!=nil{return err}
  leafName:=fmt.Sprintf("leaf-%d.ascii",index)
  if err:=writeFile(out,leafName,leafBuf.Bytes()); err!=nil{return err}
  h:=leaf.ToHash()
  inclusion,err:=cli.GetInclusionProof(ctx,requests.InclusionProof{Size:cth.Size,LeafHash:h}); if err!=nil{return err}
  incResp,err:=tap.last("get-inclusion-proof"); if err!=nil{return err}
  if inclusion.LeafIndex!=index {return fmt.Errorf("HOLD_INCLUSION_INDEX_%d",index)}
  if err:=inclusion.Verify(&h,&cth.TreeHead); err!=nil{return fmt.Errorf("HOLD_INCLUSION_%d: %w",index,err)}
  incName:=fmt.Sprintf("inclusion-%d.raw",index)
  if err:=writeFile(out,incName,incResp.Body); err!=nil{return err}
  leafPins=append(leafPins,leafPin{Index:index,Checksum:checksum,LeafFile:leafName,InclusionFile:incName})
 }
 names:=[]string{"checkpoint.raw","checkpoint.canonical","consistency-281653.raw","consistency-281670.raw","leaves.raw"}
 for _,lp:=range leafPins {names=append(names,lp.LeafFile,lp.InclusionFile)}
 hashes,err:=fileHashes(out,names); if err!=nil{return err}
 m:=manifest{Schema:"ARIO-A15-COSIGNED-CHECKPOINT-HANDOFF-v1",CapturedAtUTC:time.Now().UTC().Format(time.RFC3339Nano),RunnerClockAttested:false,LogURL:logURL,CheckpointURL:headResp.URL,CheckpointHTTPStatus:headResp.Status,TreeSize:cth.Size,RootHash:hex.EncodeToString(cth.RootHash[:]),CosignatureCount:len(cth.Cosignatures),Floors:floors,Leaves:leafPins,Files:hashes,Publication:"NONE",Signing:"NONE",Freshness:"UNKNOWN",GlobalLatest:"NOT_ESTABLISHED",IndependentCustody:"NOT_ESTABLISHED",TrustActivation:"NO_GO",Production:"NO_GO"}
 mb,err:=json.MarshalIndent(m,"","  "); if err!=nil{return err}
 if err:=writeFile(out,"manifest.json",append(mb,'\n')); err!=nil{return err}
 return verifyBundle(out)
}
func verifyBundle(root string) error {
 rawManifest,err:=readFile(root,"manifest.json"); if err!=nil{return err}
 dec:=json.NewDecoder(bytes.NewReader(rawManifest)); dec.DisallowUnknownFields()
 var m manifest; if err:=dec.Decode(&m); err!=nil{return err}
 var extra any; if err:=dec.Decode(&extra); err!=io.EOF{return fmt.Errorf("HOLD_MANIFEST_TRAILING")}
 if m.Schema!="ARIO-A15-COSIGNED-CHECKPOINT-HANDOFF-v1" || m.RunnerClockAttested || m.LogURL!=logURL || m.CheckpointHTTPStatus!=http.StatusOK || !strings.HasPrefix(m.CheckpointURL,logURL+"/") || m.Publication!="NONE" || m.Signing!="NONE" || m.Freshness!="UNKNOWN" || m.GlobalLatest!="NOT_ESTABLISHED" || m.IndependentCustody!="NOT_ESTABLISHED" || m.TrustActivation!="NO_GO" || m.Production!="NO_GO" {return fmt.Errorf("HOLD_MANIFEST_POLICY")}
 if len(m.Files)!=11 || len(m.Floors)!=2 || len(m.Leaves)!=3 || m.TreeSize<=floorB || m.CosignatureCount<2 {return fmt.Errorf("HOLD_MANIFEST_COUNTS")}
 expectedFiles:=map[string]bool{"checkpoint.raw":true,"checkpoint.canonical":true,"consistency-281653.raw":true,"consistency-281670.raw":true,"leaves.raw":true}
 for i:=0;i<3;i++ {idx:=firstIndex+uint64(i);expectedFiles[fmt.Sprintf("leaf-%d.ascii",idx)]=true;expectedFiles[fmt.Sprintf("inclusion-%d.raw",idx)]=true}
 for name,want:=range m.Files {if !expectedFiles[name] {return fmt.Errorf("HOLD_UNEXPECTED_PATH")};b,e:=readFile(root,name); if e!=nil{return e}; if digest(b)!=want{return fmt.Errorf("HOLD_FILE_DIGEST_%s",name)}}
 for name:=range expectedFiles {if _,ok:=m.Files[name];!ok{return fmt.Errorf("HOLD_MISSING_PATH_%s",name)}}
 if m.Floors[0]!=(floorPin{Size:floorA,Root:floorARoot,ProofFile:"consistency-281653.raw"}) || m.Floors[1]!=(floorPin{Size:floorB,Root:floorBRoot,ProofFile:"consistency-281670.raw"}) {return fmt.Errorf("HOLD_FLOOR_PINS")}
 raw,err:=readFile(root,"checkpoint.raw"); if err!=nil{return err}
 var cth types.CosignedTreeHead; if err:=cth.FromASCII(bytes.NewReader(raw)); err!=nil{return fmt.Errorf("HOLD_CTH_PARSE: %w",err)}
 p:=loadPolicy(); logKH:=mustHash(logKeyHashHex)
 if err:=p.VerifyCosignedTreeHead(&logKH,&cth); err!=nil{return fmt.Errorf("HOLD_CTH_VERIFY: %w",err)}
 if cth.Size!=m.TreeSize || hex.EncodeToString(cth.RootHash[:])!=m.RootHash || len(cth.Cosignatures)!=m.CosignatureCount || len(cth.Cosignatures)<2 {return fmt.Errorf("HOLD_CTH_MANIFEST_MISMATCH")}
 canonical,err:=readFile(root,"checkpoint.canonical"); if err!=nil{return err}
 var canonicalCTH types.CosignedTreeHead
 if err:=canonicalCTH.FromASCII(bytes.NewReader(canonical)); err!=nil{return fmt.Errorf("HOLD_CANONICAL_PARSE: %w",err)}
 if err:=p.VerifyCosignedTreeHead(&logKH,&canonicalCTH); err!=nil{return fmt.Errorf("HOLD_CANONICAL_VERIFY: %w",err)}
 if canonicalCTH.Size!=cth.Size || canonicalCTH.RootHash!=cth.RootHash || len(canonicalCTH.Cosignatures)!=len(cth.Cosignatures) {return fmt.Errorf("HOLD_CANONICAL_MISMATCH")}
 for _,f:=range m.Floors {
  oldRoot,e:=parseHash(f.Root); if e!=nil{return e}
  old:=types.TreeHead{Size:f.Size,RootHash:oldRoot}
  proofBytes,e:=readFile(root,f.ProofFile); if e!=nil{return e}
  var proof types.ConsistencyProof
  if e:=proof.FromASCII(bytes.NewReader(proofBytes)); e!=nil{return fmt.Errorf("HOLD_PROOF_PARSE_%d: %w",f.Size,e)}
  if e:=proof.Verify(&old,&cth.TreeHead); e!=nil{return fmt.Errorf("HOLD_PROOF_VERIFY_%d: %w",f.Size,e)}
 }
 pub,signerHash:=signer()
 rawLeavesBytes,e:=readFile(root,"leaves.raw"); if e!=nil{return e}
 rawLeaves,e:=types.LeavesFromASCII(bytes.NewReader(rawLeavesBytes),3); if e!=nil{return fmt.Errorf("HOLD_RAW_LEAVES_PARSE: %w",e)}
 if len(rawLeaves)!=3{return fmt.Errorf("HOLD_RAW_LEAVES_COUNT")}
 for i,lp:=range m.Leaves {
  index:=firstIndex+uint64(i)
  if lp.Index!=index || lp.Checksum!=expectedChecksums[i] || lp.LeafFile!=fmt.Sprintf("leaf-%d.ascii",index) || lp.InclusionFile!=fmt.Sprintf("inclusion-%d.raw",index) {return fmt.Errorf("HOLD_LEAF_MANIFEST_%d",index)}
  leafBytes,e:=readFile(root,lp.LeafFile); if e!=nil{return e}
  parsedLeaves,e:=types.LeavesFromASCII(bytes.NewReader(leafBytes),1); if e!=nil{return e}; if len(parsedLeaves)!=1{return fmt.Errorf("HOLD_LEAF_COUNT_%d",index)}
  leaf:=parsedLeaves[0]
  if !bytes.Equal(rawLeaves[i].ToBinary(),leaf.ToBinary()) {return fmt.Errorf("HOLD_RAW_CANONICAL_LEAF_MISMATCH_%d",index)}
  if hex.EncodeToString(leaf.Checksum[:])!=lp.Checksum || leaf.KeyHash!=signerHash || !leaf.Verify(&pub) {return fmt.Errorf("HOLD_LEAF_VERIFY_%d",index)}
  incBytes,e:=readFile(root,lp.InclusionFile); if e!=nil{return e}
  var inc types.InclusionProof; if e:=inc.FromASCII(bytes.NewReader(incBytes)); e!=nil{return e}
  h:=leaf.ToHash()
  if inc.LeafIndex!=index {return fmt.Errorf("HOLD_INCLUSION_INDEX_%d",index)}
  if e:=inc.Verify(&h,&cth.TreeHead); e!=nil{return fmt.Errorf("HOLD_INCLUSION_VERIFY_%d: %w",index,e)}
 }
 report:=map[string]any{"status":"VERIFIED_AUTHENTIC_COSIGNED_CHECKPOINT_AND_RETAINED_PROOFS","tree_size":cth.Size,"root_hash":m.RootHash,"cosignatures":len(cth.Cosignatures),"floors_verified":[]uint64{floorA,floorB},"a15_leaves_verified":len(m.Leaves),"publication":"NONE","signing":"NONE","freshness":"UNKNOWN","global_latest":"NOT_ESTABLISHED","independent_custody":"NOT_ESTABLISHED","trust_activation":"NO_GO","production":"NO_GO"}
 rb,_:=json.MarshalIndent(report,"","  ")
 return writeFile(root,"verification.json",append(rb,'\n'))
}
func main() {
 if len(os.Args)!=3 {log.Fatal("usage: capture <new-output-dir> | verify <bundle-dir>")}
 var err error
 switch os.Args[1] {case "capture":err=capture(os.Args[2]);case "verify":err=verifyBundle(os.Args[2]);default:err=fmt.Errorf("HOLD_COMMAND")}
 if err!=nil {log.Fatal(err)}
 if os.Args[1]=="capture" {b,_:=os.ReadFile(filepath.Join(os.Args[2],"verification.json"));fmt.Println(string(b))} else {fmt.Println("OFFLINE_CHECKPOINT_BUNDLE_VERIFIED")}
}
