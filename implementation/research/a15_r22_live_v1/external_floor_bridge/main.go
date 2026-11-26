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
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"sigsum.org/sigsum-go/pkg/client"
	"sigsum.org/sigsum-go/pkg/crypto"
	"sigsum.org/sigsum-go/pkg/requests"
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

type externalFloorRecord struct {
	Schema string `json:"schema"`
	SourceWorkflowRun int64 `json:"source_workflow_run"`
	SigsumLog string `json:"sigsum_log"`
	LogKeyHash string `json:"log_key_hash"`
	ExternalFloor struct {
		TreeSize uint64 `json:"tree_size"`
		RootHash string `json:"root_hash"`
	} `json:"external_floor"`
	CustodianReadback struct {
		TreeSize uint64 `json:"tree_size"`
		RootHash string `json:"root_hash"`
		Matches bool `json:"matches_cosigned_head"`
	} `json:"custodian_readback"`
	ExternalWitnesses []struct {
		Name string `json:"name"`
		SignatureValid bool `json:"signature_valid"`
	} `json:"verified_external_cosigners"`
	CustomPolicy string `json:"custom_research_policy"`
	BuiltinPolicy string `json:"builtin_sigsum_test2_2025"`
	DataAvailability string `json:"data_availability"`
	GlobalLatest string `json:"global_latest"`
	Admission bool `json:"admission"`
	PublicationPerformed bool `json:"publication_performed"`
	TrustActivation string `json:"trust_activation"`
	Production string `json:"production"`
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

func verifyOfficial(proof, eventID, pubkey, temp string, label string) {
	proofPath := filepath.Join(temp, label+".proof")
	pubPath := filepath.Join(temp, label+".pub")
	if err := os.WriteFile(proofPath, proof, 0600); err != nil { fail("write proof: %v", err) }
	if err := os.WriteFile(pubPath, pubkey, 0600); err != nil { fail("write key: %v", err) }
	cmd := exec.Command("sigsum-verify", "-k", pubPath, "-P", "sigsum-test1-2025", proofPath)
	cmd.Stdin = bytes.NewReader(eventID)
	output, err := cmd.CombinedOutput()
	if err != nil { fail("official Sigsum verifier rejected %s proof: %v: %s", label, err, strings.TrimSpace(string(output))) }
	fmt.Printf("%s_OFFICIAL_SIGSUM_VERIFY PASS\n", strings.ToUpper(label))
}

func mustHash(value string) crypto.Hash {
	b, err := hex.DecodeString(value)
	if err != nil || len(b) != 32 { fail("invalid pinned hash") }
	var h crypto.Hash
	copy(h[:], b)
	return h
}

func main() {
	firstPath := flag.String("first-zip", "", "pinned original A15 first-checkpoint artifact")
	secondPath := flag.String("second-zip", "", "pinned original A15 second-checkpoint artifact")
	floorPath := flag.String("external-floor-json", "", "pinned R22.22I external floor record")
	flag.Parse()
	if *firstPath == "" || *secondPath == "" || *floorPath == "" { fail("missing input paths") }

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

	temp, err := os.MkdirTemp("", "ario-a15-external-floor-")
	if err != nil { fail("temporary directory: %v", err) }
	defer os.RemoveAll(temp)
	verifyOfficial(first["event-id.txt.proof"], first["event-id.txt"], first["log-key.pub"], temp, "first")
	verifyOfficial(second["event-id.txt.proof"], second["event-id.txt"], first["log-key.pub"], temp, "second")

	rawFloor, err := os.ReadFile(*floorPath)
	if err != nil { fail("read external floor record: %v", err) }
	var floor externalFloorRecord
	if err := json.Unmarshal(rawFloor, &floor); err != nil { fail("external floor JSON: %v", err) }
	if floor.Schema != "ario.r22.22i.external-floor.v1" || floor.SourceWorkflowRun != 45838457364 { fail("wrong external floor record identity") }
	if floor.SigsumLog != logURL || floor.LogKeyHash != logID { fail("A15 and R22.22I do not name the same Sigsum log") }
	if floor.ExternalFloor.TreeSize != externalSize || floor.ExternalFloor.RootHash != externalRoot { fail("external floor coordinates mismatch") }
	if !floor.CustodianReadback.Matches || floor.CustodianReadback.TreeSize != externalSize || floor.CustodianReadback.RootHash != externalRoot { fail("Remora readback does not match external signed head") }
	if floor.CustomPolicy != "2-of-4 external-only; Glasklar excluded" || floor.BuiltinPolicy != "NOT_MET" { fail("external witness policy disposition mismatch") }
	if floor.Admission || floor.PublicationPerformed || floor.TrustActivation != "NO_GO" || floor.Production != "NO_GO" || floor.DataAvailability != "NOT_PROVEN" || floor.GlobalLatest != "UNKNOWN" { fail("external floor limitations/status changed") }
	valid := map[string]bool{}
	for _, w := range floor.ExternalWitnesses { if w.SignatureValid { valid[w.Name] = true } }
	if len(valid) != 2 || !valid["remora.n621.de"] || !valid["witness.stagemole.eu"] { fail("expected two distinct external witness cosigners not present in pinned record") }
	if p2.Size >= floor.ExternalFloor.TreeSize { fail("external floor is not newer than A15 checkpoint") }
	fmt.Println("PINNED_R22_22I_EXTERNAL_FLOOR_AND_TWO_WITNESSES PASS")

	oldHead := types.TreeHead{Size: p2.Size, RootHash: mustHash(p2.Root)}
	newHead := types.TreeHead{Size: floor.ExternalFloor.TreeSize, RootHash: mustHash(floor.ExternalFloor.RootHash)}
	ctx, cancel := context.WithTimeout(context.Background(), 45*time.Second)
	defer cancel()
	httpClient := &http.Client{Timeout: 15*time.Second, CheckRedirect: func(*http.Request, []*http.Request) error { return errors.New("redirect refused") }}
	cli := client.New(client.Config{URL: logURL, HTTPClient: httpClient})
	proof, err := cli.GetConsistencyProof(ctx, requests.ConsistencyProof{OldSize: oldHead.Size, NewSize: newHead.Size})
	if err != nil { fail("fetch Sigsum consistency proof %d->%d: %v", oldHead.Size, newHead.Size, err) }
	if err := proof.Verify(&oldHead, &newHead); err != nil { fail("A15 head is not a prefix of external witness floor: %v", err) }
	fmt.Println("A15_HEAD_TO_EXTERNAL_WITNESS_FLOOR_CONSISTENCY PASS")

	out := map[string]any{
		"schema": "ARIO_A15_R22_EXTERNAL_WITNESS_BRIDGE_V1",
		"status": "PASS_A15_PREFIX_OF_EXTERNALLY_WITNESSED_FLOOR",
		"same_sigsum_log_id": logID,
		"a15_head": map[string]any{"tree_size": p2.Size, "root_hash": p2.Root, "leaf_index": p2.Index},
		"external_floor": map[string]any{"tree_size": floor.ExternalFloor.TreeSize, "root_hash": floor.ExternalFloor.RootHash},
		"consistency_proof": "VERIFIED",
		"witnesses": []string{"remora.n621.de", "witness.stagemole.eu"},
		"witness_run": floor.SourceWorkflowRun,
		"remora_status_readback": "EXACT_SIZE_AND_ROOT_MATCH",
		"limitations": []string{"TEST_ONLY witness network", "custom external-only 2-of-4 research policy; built-in test2 4-of-5 NOT_MET", "Remora test VM has no HSM or redundancy", "Stagemole is a best-effort test witness", "data availability NOT_PROVEN", "global_latest UNKNOWN", "no evidence admission, trust activation, or production"},
	}
	encoded, err := json.Marshal(out)
	if err != nil { fail("encode result: %v", err) }
	fmt.Println(string(encoded))
}

func mustDecodeHex(value string) []byte {
	b, err := hex.DecodeString(value)
	if err != nil { fail("invalid bootstrap public key hex") }
	return b
}
