package main
import (
 "context"
 "encoding/hex"
 "encoding/json"
 "fmt"
 "io"
 "net/http"
 "os"
 "sort"
 "strconv"
 "strings"
 "time"
 "sigsum.org/sigsum-go/pkg/client"
 "sigsum.org/sigsum-go/pkg/crypto"
 "sigsum.org/sigsum-go/pkg/policy"
 "sigsum.org/sigsum-go/pkg/requests"
 "sigsum.org/sigsum-go/pkg/types"
)
const (
 logURL="https://test.sigsum.org/barreleye"
 logPublicKeyHex="4644af2abd40f4895a003bca350f9d5912ab301a49c77f13e5b6d905c20a5fe6"
 logKeyHash="4e89cc51651f0d95f3c6127c15e1a42e3ddf7046c5b17b752689c402e773bb4d"
 retainedSize uint64=282808
 retainedRoot="6653d7a489d9988554eae8679a677f84c7a18074dbcc3a7b185773a5e83a1e4d"
)
const policyText = "log 4644af2abd40f4895a003bca350f9d5912ab301a49c77f13e5b6d905c20a5fe6 https://test.sigsum.org/barreleye\n"+
"witness poc.sigsum.org/nisse 1c25f8a44c635457e2e391d1efbca7d4c2951a0aef06225a881e46b98962ac6c\n"+
"witness rgdd.se/poc-witness 28c92a5a3a054d317c86fc2eeb6a7ab2054d6217100d0be67ded5b74323c5806\n"+
"witness witness1.smartit.nu/witness1 f4855a0f46e8a3e23bb40faf260ee57ab8a18249fa402f2ca2d28a60e1a3130e\n"+
"witness navigli.sunlight.geomys.org/dev b20196b937a30d19f0cb7dfa2d5388bc8ddde9cc3df4c24fcf63db27a573d3f2\n"+
"witness remora.n621.de ebcdeb78e7fdb2ef9227b2c1ef11e94600b55b4d6d9a57877e31ee89e59adc36\n"+
"witness witness.stagemole.eu 4a921b7caef58ae670cdc11ef4184f1c058f7b9259a9107a969f69fa54aa496f\n"+
"witness tillitis.se/test-witness-1 5c35281928e9da396beede5f22a2251a589e6ac6de52a4de85de8634ffccaf6d\n"+
"group glasklar-test-witnesses 2 poc.sigsum.org/nisse rgdd.se/poc-witness witness1.smartit.nu/witness1\n"+
"group quorum-rule 4 glasklar-test-witnesses navigli.sunlight.geomys.org/dev remora.n621.de witness.stagemole.eu tillitis.se/test-witness-1\n"+
"quorum quorum-rule\n"
type externalWitness struct { Name, Operator, URL, PublicKeyHex string }
type witnessResult struct { Name, Operator, URL string; CosignatureValid bool; StoredSize uint64; Readback string }
var external=[]externalWitness{
 {"navigli.sunlight.geomys.org/dev","Filippo Valsorda / Geomys","https://witness.navigli.sunlight.geomys.org","b20196b937a30d19f0cb7dfa2d5388bc8ddde9cc3df4c24fcf63db27a573d3f2"},
 {"remora.n621.de","Florian Larysch","https://remora.n621.de","ebcdeb78e7fdb2ef9227b2c1ef11e94600b55b4d6d9a57877e31ee89e59adc36"},
 {"witness.stagemole.eu","Grégoire Détrez","https://witness.stagemole.eu","4a921b7caef58ae670cdc11ef4184f1c058f7b9259a9107a969f69fa54aa496f"},
 {"tillitis.se/test-witness-1","Tillitis AB","https://tillitis.se/test-witness-1","5c35281928e9da396beede5f22a2251a589e6ac6de52a4de85de8634ffccaf6d"},
}
func mustHash(s string) crypto.Hash { b,e:=hex.DecodeString(s);if e!=nil||len(b)!=32{panic("bad fixed hash")};var h crypto.Hash;copy(h[:],b);return h }
func parseWitnessSize(raw []byte)(uint64,error){
 if len(raw)==0||len(raw)>4096{return 0,fmt.Errorf("response bounds")}
 value:=strings.TrimSpace(string(raw))
 if strings.HasPrefix(value,"size="){value=strings.TrimPrefix(value,"size=")}
 if value==""||strings.Contains(value,"="){return 0,fmt.Errorf("invalid size response")}
 n,e:=strconv.ParseUint(value,10,64);if e!=nil{return 0,fmt.Errorf("invalid size")};return n,nil
}
func readWitnessSize(ctx context.Context,w externalWitness)(uint64,error){
 req,e:=http.NewRequestWithContext(ctx,http.MethodGet,w.URL+"/get-tree-size/"+logKeyHash,nil);if e!=nil{return 0,e}
 req.Header.Set("Cache-Control","no-cache, no-store")
 resp,e:=(&http.Client{Timeout:12*time.Second,CheckRedirect:func(*http.Request,[]*http.Request)error{return fmt.Errorf("redirect denied")}}).Do(req)
 if e!=nil{return 0,e};defer resp.Body.Close()
 if resp.StatusCode!=http.StatusOK{return 0,fmt.Errorf("HTTP %d",resp.StatusCode)}
 raw,e:=io.ReadAll(io.LimitReader(resp.Body,4097));if e!=nil{return 0,e};return parseWitnessSize(raw)
}
func floorDecision(fs uint64,fr string,cs uint64,cr string)string{
 if cs<fs{return "HOLD_BELOW_EXTERNAL_FLOOR"};if cs==fs&&cr!=fr{return "HOLD_SAME_SIZE_ROOT_CONFLICT"};return "SIZE_AND_ROOT_NOT_BELOW_FLOOR"
}
func main(){
 p,e:=policy.ParseConfig(strings.NewReader(policyText));if e!=nil{panic(e)}
 logPub,e:=crypto.PublicKeyFromHex(logPublicKeyHex);if e!=nil{panic(e)}
 logKH:=crypto.HashBytes(logPub[:]);if hex.EncodeToString(logKH[:])!=logKeyHash{panic("log key hash mismatch")}
 ctx,cancel:=context.WithTimeout(context.Background(),150*time.Second);defer cancel()
 cli:=client.New(client.Config{URL:logURL,HTTPClient:&http.Client{Timeout:12*time.Second,CheckRedirect:func(*http.Request,[]*http.Request)error{return fmt.Errorf("redirect denied")}}})
 head,e:=cli.GetTreeHead(ctx);if e!=nil{panic("HOLD_LOG_READBACK: "+e.Error())}
 test2Result:="PASS"
 if e=p.VerifyCosignedTreeHead(&logKH,&head);e!=nil{test2Result="NOT_MET: "+e.Error()}
 externalPubs:=make([]crypto.PublicKey,0,len(external))
 for _,w:=range external{pub,pe:=crypto.PublicKeyFromHex(w.PublicKeyHex);if pe!=nil{panic(pe)};externalPubs=append(externalPubs,pub)}
 externalPolicy,e:=policy.NewKofNPolicy([]crypto.PublicKey{logPub},externalPubs,2)
 if e!=nil{panic(e)}
 if e=externalPolicy.VerifyCosignedTreeHead(&logKH,&head);e!=nil{panic("HOLD_EXTERNAL_ONLY_2_OF_4_QUORUM: "+e.Error())}
 retained:=types.TreeHead{Size:retainedSize,RootHash:mustHash(retainedRoot)}
 if head.Size<retained.Size{panic("HOLD_HEAD_BELOW_RETAINED")}
 if head.Size==retained.Size {if head.RootHash!=retained.RootHash{panic("HOLD_SAME_SIZE_ROOT_CONFLICT")}} else {
  pr,e:=cli.GetConsistencyProof(ctx,requests.ConsistencyProof{OldSize:retained.Size,NewSize:head.Size});if e!=nil{panic("HOLD_RETAINED_CONSISTENCY: "+e.Error())}
  if e=pr.Verify(&retained,&head.TreeHead);e!=nil{panic("HOLD_RETAINED_CONSISTENCY: "+e.Error())}
 }
 known:=make(map[string]crypto.PublicKey)
 for _,ent:=range p.GetWitnesses(){kh:=crypto.HashBytes(ent.PublicKey[:]);known[hex.EncodeToString(kh[:])]=ent.PublicKey}
 origin:=types.SigsumCheckpointOrigin(&logPub)
 results:=make([]witnessResult,0,len(external));accepted:=make([]uint64,0,len(external))
 for _,w:=range external{
  result:=witnessResult{Name:w.Name,Operator:w.Operator,URL:w.URL,Readback:"NO_VALID_COSIGNATURE"}
  pub,e:=crypto.PublicKeyFromHex(w.PublicKeyHex);if e!=nil{panic(e)}
  kh:=crypto.HashBytes(pub[:]);cs,ok:=head.Cosignatures[kh]
  if ok&&cs.Verify(&pub,origin,&head.TreeHead){
   result.CosignatureValid=true
   if k,exists:=known[hex.EncodeToString(kh[:])];!exists||k!=pub{panic("HOLD_POLICY_KEY_BINDING: "+w.Name)}
   size,re:=readWitnessSize(ctx,w)
   if re!=nil{result.Readback="HOLD_READBACK: "+re.Error()}else{
    result.StoredSize=size
    if size<head.Size{result.Readback="HOLD_WITNESS_BELOW_ITS_COSIGNED_HEAD"}else{result.Readback="PASS_STORED_SIZE_AT_OR_ABOVE_COSIGNED_HEAD";accepted=append(accepted,size)}
   }
  }
  results=append(results,result)
 }
 if len(accepted)<2{
  diagnostic:=map[string]any{"result":"HOLD_EXTERNAL_WITNESS_READBACKS","valid_external_readbacks":len(accepted),"built_in_test2_diagnostic":test2Result,"head_size":head.Size,"head_root":hex.EncodeToString(head.RootHash[:]),"external_witnesses":results}
  _=json.NewEncoder(os.Stdout).Encode(diagnostic)
  panic(fmt.Sprintf("HOLD_EXTERNAL_WITNESS_READBACKS: %d/4, need 2",len(accepted)))
 }
 sort.Slice(accepted,func(i,j int)bool{return accepted[i]>accepted[j]})
 minTwo:=accepted[1];if minTwo<head.Size{panic("HOLD_EXTERNAL_QUORUM_FLOOR_BELOW_HEAD")}
 root:=hex.EncodeToString(head.RootHash[:])
 if floorDecision(head.Size,root,head.Size-1,"arbitrary")!="HOLD_BELOW_EXTERNAL_FLOOR"{panic("HOLD_ROLLBACK_CONTROL")}
 if floorDecision(head.Size,root,head.Size,strings.Repeat("0",64))!="HOLD_SAME_SIZE_ROOT_CONFLICT"{panic("HOLD_SAME_SIZE_CONTROL")}
 out:=map[string]any{
  "result":"EXTERNAL_TEST_WITNESS_QUORUM_READBACK_PASS","policy":"custom external-only 2-of-4 over the four test2 external public keys",
  "built_in_sigsum_test2_2025":"NOT_USED_AS_ACCEPTANCE_POLICY",
  "built_in_test2_diagnostic":test2Result,
  "policy_quorum":"2-of-4 external witnesses only; Glasklar group is excluded",
  "head_size":head.Size,"head_root":root,"retained_floor_size":retainedSize,"retained_floor_root":retainedRoot,
  "external_witnesses":results,"minimum_two_external_stored_size":minTwo,
  "independent_quorum_floor_size":head.Size,"independent_quorum_floor_root":root,
  "rollback_below_floor":"HOLD","same_size_different_root":"HOLD",
  "data_availability":"NOT_PROVEN_BY_WITNESSES","global_latest":"UNKNOWN","network_tier":"TEST_ONLY",
  "trust_activation":"NO_GO","production":"NO_GO","admission":false,
 }
 enc:=json.NewEncoder(os.Stdout);enc.SetEscapeHTML(false);if e=enc.Encode(out);e!=nil{panic(e)}
}
