package main

import (
	"archive/zip"
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"sort"
	"bufio"
	"encoding/base64"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"sigsum.org/sigsum-go/pkg/client"
	"sigsum.org/sigsum-go/pkg/crypto"
	"sigsum.org/sigsum-go/pkg/requests"
	"sigsum.org/sigsum-go/pkg/policy"
	"sigsum.org/sigsum-go/pkg/types"
)

const (
	logURL = "https://test.sigsum.org/barreleye"
	logID = "4e89cc51651f0d95f3c6127c15e1a42e3ddf7046c5b17b752689c402e773bb4d"
	firstZipSHA = "f6012b78741a23992be901141fb8eb560f7010d17ecc4ccf4e71d3f917cd5f97"
	secondZipSHA = "4eec66aeb8036e9628094acbe815c7418e88836d064b384dcd0558ed4910f3ec"
	firstRoot = "a22c530084d2f025d28102a1178048fdfde039a78eccec2602536b3a139e37af"
	secondRoot = "4a75206b4b69142d1d90a284420d64cabf11ebe09931ba8e97262e2ad7baa1d5"
	externalRoot = "748c0c608c8f691fd7e9a9b9d98e920f9a529f3dbcaf180109e5bcacb597196b"
	firstSize uint64 = 282773
	secondSize uint64 = 282774
	externalSize uint64 = 282813
	firstIndex uint64 = 282772
	secondIndex uint64 = 282773
)

type proofFields struct {
	Log string
	Leaf string
	Size uint64
	Root string
	Index uint64
}

func fail(format string, args ...any) {
	fmt.Fprintf(os.Stderr, "HOLD: "+format+"\n", args...)
	os.Exit(2)
}

func readZip(path, expectedSHA string, expectedNames []string) map[string][]byte {
	raw, err := os.ReadFile(path)
	if err != nil { fail("read archive %s: %v", path, err) }
	if len(raw) == 0 || len(raw) > 1<<20 { fail("archive bounds: %s", path) }
	sum := sha256.Sum256(raw)
	if hex.EncodeToString(sum[:]) != expectedSHA { fail("archive SHA256 mismatch: %s", path) }
	zr, err := zip.NewReader(bytes.NewReader(raw), int64(len(raw)))
	if err != nil { fail("ZIP parse %s: %v", path, err) }
	if len(zr.File) != len(expectedNames) { fail("archive member count mismatch: %s", path) }
	expected := make(map[string]bool, len(expectedNames))
	for _, name := range expectedNames { expected[name] = true }
	out := make(map[string][]byte, len(expectedNames))
	var total uint64
	for _, f := range zr.File {
		if !expected[f.Name] || out[f.Name] != nil || f.Mode()&os.ModeSymlink != 0 { fail("unexpected/duplicate/symlink member: %s", f.Name) }
		if f.UncompressedSize64 > 128*1024 { fail("member too large: %s", f.Name) }
		total += f.UncompressedSize64
		if total > 128*1024 { fail("archive expansion limit") }
		rc, err := f.Open()
		if err != nil { fail("open member %s: %v", f.Name, err) }
		b, err := io.ReadAll(io.LimitReader(rc, int64(f.UncompressedSize64)+1))
		closeErr := rc.Close()
		if err != nil || closeErr != nil || uint64(len(b)) != f.UncompressedSize64 { fail("read/CRC/size member %s: %v", f.Name, errors.Join(err, closeErr)) }
		out[f.Name] = b
	}
	for name := range expected { if _, ok := out[name]; !ok { fail("missing archive member: %s", name) } }
	return out
}

func parseProof(raw []byte) proofFields {
	fields := map[string]string{}
	repeated := map[string]bool{"cosignature": true, "node_hash": true}
	allowed := map[string]bool{"version": true, "log": true, "leaf": true, "size": true, "root_hash": true, "signature": true, "leaf_index": true, "cosignature": true, "node_hash": true}
	for _, line := range strings.Split(string(raw), "\n") {
		if line == "" { continue }
		key, value, ok := strings.Cut(line, "=")
		if !ok || !allowed[key] { fail("invalid proof field") }
		if repeated[key] { continue }
		if _, exists := fields[key]; exists { fail("duplicate proof field: %s", key) }
		fields[key] = value
	}
	required := []string{"version", "log", "leaf", "size", "root_hash", "signature", "leaf_index"}
	if len(fields) != len(required) { fail("proof required-field count") }
	for _, key := range required { if fields[key] == "" { fail("missing proof field: %s", key) } }
	if fields["version"] != "2" || fields["log"] != logID { fail("wrong Sigsum version/log ID") }
	leaf := strings.Fields(fields["leaf"])
	if len(leaf) != 2 || len(leaf[0]) != 64 || len(leaf[1]) != 128 { fail("invalid leaf shape") }
	if _, err := hex.DecodeString(leaf[0]); err != nil { fail("invalid leaf key hash") }
	if _, err := hex.DecodeString(leaf[1]); err != nil { fail("invalid leaf signature") }
	root, err := hex.DecodeString(fields["root_hash"])
	if err != nil || len(root) != 32 { fail("invalid root hash") }
	size, err := strconv.ParseUint(fields["size"], 10, 64)
	if err != nil { fail("invalid tree size") }
	index, err := strconv.ParseUint(fields["leaf_index"], 10, 64)
	if err != nil || index >= size { fail("invalid leaf index") }
	return proofFields{Log: fields["log"], Leaf: leaf[0], Size: size, Root: fields["root_hash"], Index: index}
}

func verifyOfficial(proof, eventID, pubkey []byte, temp string, label string, policyPath string) {
	proofPath := filepath.Join(temp, label+".proof")
	pubPath := filepath.Join(temp, label+".pub")
	if err := os.WriteFile(proofPath, proof, 0600); err != nil { fail("write proof: %v", err) }
	if err := os.WriteFile(pubPath, pubkey, 0600); err != nil { fail("write key: %v", err) }
	cmd := exec.Command("sigsum-verify", "-k", pubPath, "-p", policyPath, proofPath)
	cmd.Stdin = bytes.NewReader(eventID)
	output, err := cmd.CombinedOutput()
	if err != nil { fail("official Sigsum verifier rejected %s proof: %v: %s", label, err, strings.TrimSpace(string(output))) }
	fmt.Printf("%s_OFFICIAL_EXTERNAL_QUORUM_VERIFY PASS\n", strings.ToUpper(label))
}

func mustHash(value string) crypto.Hash {
	b, err := hex.DecodeString(value)
	if err != nil || len(b) != 32 { fail("invalid pinned hash") }
	var h crypto.Hash
	copy(h[:], b)
	return h
}


const logPubHex = "4644af2abd40f4895a003bca350f9d5912ab301a49c77f13e5b6d905c20a5fe6"

var witnessKeys = map[string]string{
 "geomys": "b20196b937a30d19f0cb7dfa2d5388bc8ddde9cc3df4c24fcf63db27a573d3f2",
 "remora": "ebcdeb78e7fdb2ef9227b2c1ef11e94600b55b4d6d9a57877e31ee89e59adc36",
 "stagemole": "4a921b7caef58ae670cdc11ef4184f1c058f7b9259a9107a969f69fa54aa496f",
 "tillitis": "5c35281928e9da396beede5f22a2251a589e6ac6de52a4de85de8634ffccaf6d",
}

func externalPolicy() string {
 return "log "+logPubHex+"\n"+
 "witness geomys "+witnessKeys["geomys"]+"\n"+
 "witness remora "+witnessKeys["remora"]+"\n"+
 "witness stagemole "+witnessKeys["stagemole"]+"\n"+
 "witness tillitis "+witnessKeys["tillitis"]+"\n"+
 "group external 1 geomys stagemole tillitis\n"+
 "group required 2 remora external\n"+
 "quorum required\n"
}

func authenticate(head *types.CosignedTreeHead) ([]string,error) {
 logPub,e:=crypto.PublicKeyFromHex(logPubHex);if e!=nil{return nil,e}
 kh:=crypto.HashBytes(logPub[:]);if hex.EncodeToString(kh[:])!=logID{return nil,errors.New("log pin mismatch")}
 p,e:=policy.ParseConfig(strings.NewReader(externalPolicy()));if e!=nil{return nil,e}
 if e=p.VerifyCosignedTreeHead(&kh,head);e!=nil{return nil,e}
 var names []string
 for name,key:=range witnessKeys {
  pub,e:=crypto.PublicKeyFromHex(key);if e!=nil{return nil,e}
  sig,ok:=head.Cosignatures[crypto.HashBytes(pub[:])]
  if ok&&sig.Verify(&pub,types.SigsumCheckpointOrigin(&logPub),&head.TreeHead){names=append(names,name)}
 }
 sort.Strings(names)
 return names,nil
}

func archiveHead(raw []byte) (types.CosignedTreeHead,error) {
 var head types.CosignedTreeHead
 blocks:=bytes.Split(raw,[]byte("\n\n"))
 if len(blocks)!=3{return head,errors.New("proof block count")}
 // Parse actual signed tree head and cosignatures, not a JSON report.
 e:=head.FromASCII(bytes.NewReader(append(append([]byte{},blocks[1]...),'\n')))
 return head,e
}

func verifyBinding(first,second map[string][]byte,temp string) error {
 // Reuse the existing A15 event verifier on the exact bytes passed to Sigsum.
 for _,pair:=range []struct{name string;data map[string][]byte}{{"first",first},{"second",second}} {
  d:=filepath.Join(temp,pair.name);if e:=os.Mkdir(d,0700);e!=nil{return e}
  for _,k:=range []string{"event.json","checkpoint.json","event-id.txt"} {
   if e:=os.WriteFile(filepath.Join(d,k),pair.data[k],0600);e!=nil{return e}
  }
 }
 if e:=os.WriteFile(filepath.Join(temp,"first","nostr.pub"),first["nostr.pub"],0600);e!=nil{return e}
 script, e:=filepath.Abs("bind_checkpoints.py");if e!=nil{return e}
 cmd:=exec.Command("python",script,temp)
 out,e:=cmd.CombinedOutput();if e!=nil{return fmt.Errorf("checkpoint binding: %w: %s",e,out)}
 fmt.Print(string(out));return nil
}

func consistent(ctx context.Context,cli *client.Client,old,new types.TreeHead) error {
 if old.Size>new.Size{return errors.New("rollback")}
 if old.Size==new.Size {if old.RootHash!=new.RootHash{return errors.New("same-size fork")};return nil}
 p,e:=cli.GetConsistencyProof(ctx,requests.ConsistencyProof{OldSize:old.Size,NewSize:new.Size})
 if e!=nil{return e};return p.Verify(&old,&new)
}

func readRemora(ctx context.Context,hc *http.Client) (uint64,crypto.Hash,[]byte,error) {
 var root crypto.Hash
 req,e:=http.NewRequestWithContext(ctx,http.MethodGet,"https://remora.n621.de/status",nil);if e!=nil{return 0,root,nil,e}
 req.Header.Set("Cache-Control","no-cache, no-store")
 resp,e:=hc.Do(req);if e!=nil{return 0,root,nil,e};defer resp.Body.Close()
 if resp.StatusCode!=200{return 0,root,nil,fmt.Errorf("Remora HTTP %d",resp.StatusCode)}
 raw,e:=io.ReadAll(io.LimitReader(resp.Body,(1<<20)+1));if e!=nil||len(raw)>1<<20{return 0,root,nil,errors.New("Remora read bounds")}
 sc:=bufio.NewScanner(bytes.NewReader(raw));found:=false;var size uint64
 for sc.Scan(){
  if strings.TrimSpace(sc.Text())!="- sigsum.org/v1/tree/"+logID{continue}
  if found||!sc.Scan(){return 0,root,nil,errors.New("duplicate or incomplete Remora record")}
  line:=strings.TrimSpace(sc.Text())
  if !strings.HasPrefix(line,"(size ")||!strings.HasSuffix(line,")"){return 0,root,nil,errors.New("Remora format")}
  fields:=strings.SplitN(strings.TrimSuffix(strings.TrimPrefix(line,"(size "),")"),", root ",2)
  if len(fields)!=2{return 0,root,nil,errors.New("Remora fields")}
  size,e=strconv.ParseUint(fields[0],10,64);if e!=nil{return 0,root,nil,e}
  b,e:=base64.StdEncoding.DecodeString(fields[1]);if e!=nil||len(b)!=32{return 0,root,nil,errors.New("Remora root")}
  copy(root[:],b);found=true
 }
 if sc.Err()!=nil||!found{return 0,root,nil,errors.New("Remora entry unavailable")}
 return size,root,raw,nil
}

func main() {
 firstPath:=flag.String("first-zip","","pinned first archive")
 secondPath:=flag.String("second-zip","","pinned second archive")
 evidence:=flag.String("evidence-dir","","directory for actual signed head and readback")
 flag.Parse()
 if *firstPath==""||*secondPath==""||*evidence==""{fail("missing inputs")}
	first := readZip(*firstPath, firstZipSHA, []string{"checkpoint.json","bootstrap.json","event-id.txt.proof","event-id.txt","event.json","log-key.pub","nostr.pub","sigsum.pub"})
	second := readZip(*secondPath, secondZipSHA, []string{"checkpoint.json","event-id.txt.proof","event-id.txt","event.json","matched-state/custodian.floor.json","matched-state/custodian.sqlite3","rollback-state/custodian.floor.json","rollback-state/custodian.sqlite3"})
	fmt.Println("A15_ARCHIVE_DIGESTS_AND_MANIFESTS PASS")

	p1 := parseProof(first["event-id.txt.proof"])
	p2 := parseProof(second["event-id.txt.proof"])
	if p1.Size != firstSize || p1.Root != firstRoot || p1.Index != firstIndex { fail("first A15 proof does not match pinned bootstrap head") }
	if p2.Size != secondSize || p2.Root != secondRoot || p2.Index != secondIndex { fail("second A15 proof does not match pinned successor head") }
	if p1.Log != p2.Log || p1.Leaf != p2.Leaf || p2.Index != p1.Index+1 || p2.Size <= p1.Size { fail("A15 proof sequence/signer continuity mismatch") }
	var bootstrap struct {
		FirstChecksum string `json:"first_checksum"`
		Public string `json:"public"`
		Root string `json:"root"`
		Size uint64 `json:"size"`
		Start uint64 `json:"start"`
	}
	if err := json.Unmarshal(first["bootstrap.json"], &bootstrap); err != nil { fail("bootstrap JSON: %v", err) }
	if bootstrap.Size != p1.Size || bootstrap.Root != p1.Root || bootstrap.Start != p1.Index { fail("bootstrap does not bind first A15 proof") }
	pubHash := sha256.Sum256(mustDecodeHex(bootstrap.Public))
	if hex.EncodeToString(pubHash[:]) != p1.Leaf { fail("bootstrap submitter key does not bind A15 leaf") }
	sum1 := sha256.Sum256(first["event-id.txt"])
	sum2 := sha256.Sum256(sum1[:])
	if bootstrap.FirstChecksum != hex.EncodeToString(sum2[:]) { fail("bootstrap event-ID checksum mismatch") }
	fmt.Println("A15_TWO_CHECKPOINT_PROOFS_AND_BOOTSTRAP_BINDING PASS")

 temp,e:=os.MkdirTemp("","ario-bridge-v2-");if e!=nil{fail("temp: %v",e)};defer os.RemoveAll(temp)
 if e=verifyBinding(first,second,temp);e!=nil{fail("%v",e)}
 policyPath:=filepath.Join(temp,"external.policy")
 if e=os.WriteFile(policyPath,[]byte(externalPolicy()),0600);e!=nil{fail("policy: %v",e)}
 verifyOfficial(first["event-id.txt.proof"],first["event-id.txt"],first["log-key.pub"],temp,"first",policyPath)
 verifyOfficial(second["event-id.txt.proof"],second["event-id.txt"],first["log-key.pub"],temp,"second",policyPath)
 h1,e:=archiveHead(first["event-id.txt.proof"]);if e!=nil{fail("first head: %v",e)}
 h2,e:=archiveHead(second["event-id.txt.proof"]);if e!=nil{fail("second head: %v",e)}
 if h1.Size!=p1.Size||h1.RootHash!=mustHash(p1.Root)||h2.Size!=p2.Size||h2.RootHash!=mustHash(p2.Root){fail("proof head coordinates")}
 n1,e:=authenticate(&h1);if e!=nil{fail("first cosignatures: %v",e)}
 n2,e:=authenticate(&h2);if e!=nil{fail("second cosignatures: %v",e)}
 fmt.Println("ARCHIVED_EXTERNAL_SIGNATURES_PASS",n1,n2)
 ctx,cancel:=context.WithTimeout(context.Background(),90*time.Second);defer cancel()
 hc:=&http.Client{Timeout:15*time.Second,CheckRedirect:func(*http.Request,[]*http.Request)error{return errors.New("redirect refused")}}
 cli:=client.New(client.Config{URL:logURL,HTTPClient:hc})
 historical:=types.TreeHead{Size:externalSize,RootHash:mustHash(externalRoot)}
 if e=consistent(ctx,cli,h1.TreeHead,h2.TreeHead);e!=nil{fail("seq1-to-seq2 consistency: %v",e)}
 if e=consistent(ctx,cli,h2.TreeHead,historical);e!=nil{fail("historical coordinates consistency: %v",e)}
 // Do not infer historical witness signatures from the unsigned R22.22I JSON.
 head,e:=cli.GetTreeHead(ctx);if e!=nil{fail("live signed head: %v",e)}
 names,e:=authenticate(&head);if e!=nil{fail("live signature quorum: %v",e)}
 if e=consistent(ctx,cli,historical,head.TreeHead);e!=nil{fail("historical-to-live consistency: %v",e)}
 if e=consistent(ctx,cli,h2.TreeHead,head.TreeHead);e!=nil{fail("seq2-to-live consistency: %v",e)}
 size,root,raw,e:=readRemora(ctx,hc);if e!=nil||size!=head.Size||root!=head.RootHash{fail("Remora readback: %v",e)}
 if e=os.MkdirAll(*evidence,0700);e!=nil{fail("evidence directory: %v",e)}
 var headBytes bytes.Buffer;if e=head.ToASCII(&headBytes);e!=nil{fail("serialize actual signed head: %v",e)}
 if e=os.WriteFile(filepath.Join(*evidence,"live-head.ascii"),headBytes.Bytes(),0600);e!=nil{fail("save head: %v",e)}
 if e=os.WriteFile(filepath.Join(*evidence,"remora-status.txt"),raw,0600);e!=nil{fail("save readback: %v",e)}
 out:=map[string]any{"schema":"ARIO_A15_R22_EXTERNAL_WITNESS_BRIDGE_V2","status":"PASS_DIRECT_ARCHIVED_AND_LIVE_EXTERNAL_SIGNATURES","archive_first_witnesses":n1,"archive_second_witnesses":n2,"live_witnesses":names,"live_size":head.Size,"live_root":hex.EncodeToString(head.RootHash[:]),"historical_floor_signature_bytes":"NOT_RETAINED","historical_floor_consistency":"VERIFIED","seq1_seq2_consistency":"VERIFIED","remora_readback":"EXACT_MATCH_UNSIGNED_STATUS","network":"TEST_ONLY","global_latest":"UNKNOWN","payload_custody":"NOT_ESTABLISHED","production":"NO_GO"}
 enc,e:=json.Marshal(out);if e!=nil{fail("encode: %v",e)};fmt.Println(string(enc))
}

func mustDecodeHex(value string) []byte {
	b, err := hex.DecodeString(value)
	if err != nil { fail("invalid bootstrap public key hex") }
	return b
}
