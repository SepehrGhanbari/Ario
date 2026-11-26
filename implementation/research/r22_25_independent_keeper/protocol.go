// Package main models the R22.25 external-custody protocol. It does not
// implement or claim a deployed independent custodian.
package main

import (
	"bytes"
	"context"
	"crypto/ed25519"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
)

const (
	keeperProfile = "ARIO-R22.25-KEEPER-RECEIPT-v1"
	checkpointProfile = "ARIO-R22.25-CHECKPOINT-v1"
	genesisReceipt = "0000000000000000000000000000000000000000000000000000000000000000"
)

var ErrHold = errors.New("HOLD: independent custody verification failed")
var ErrStaleHead = errors.New("HOLD: custodian compare-and-swap head changed")

type Match struct {
	Index uint64 `json:"index"`
	Checksum string `json:"checksum"`
}

type Checkpoint struct {
	Profile string `json:"profile"`
	Scope string `json:"scope"`
	Generation uint64 `json:"generation"`
	PreviousReceiptSHA256 string `json:"previous_receipt_sha256"`
	Cursor uint64 `json:"cursor"`
	TargetSize uint64 `json:"target_size"`
	TargetRoot string `json:"target_root"`
	FrontierSHA256 string `json:"frontier_sha256"`
	Matches []Match `json:"matches"`
	MatchManifestSHA256 string `json:"match_manifest_sha256"`
}

type Receipt struct {
	Profile string `json:"profile"`
	Scope string `json:"scope"`
	Generation uint64 `json:"generation"`
	PreviousReceiptSHA256 string `json:"previous_receipt_sha256"`
	CheckpointSHA256 string `json:"checkpoint_sha256"`
	CheckpointBytes uint64 `json:"checkpoint_bytes"`
	Cursor uint64 `json:"cursor"`
	TargetSize uint64 `json:"target_size"`
	TargetRoot string `json:"target_root"`
	MatchManifestSHA256 string `json:"match_manifest_sha256"`
	TransitionProofSHA256 string `json:"transition_proof_sha256,omitempty"`
	KeyID string `json:"key_id"`
	Signature string `json:"signature"`
}

type Floor struct {
	Generation uint64
	ReceiptSHA256 string
}

type Custodian interface {
	Latest(context.Context, string) (Receipt, error)
	Checkpoint(context.Context, string) ([]byte, error)
}

// VerifiedWitnessLog is an adapter contract, not an assertion about a mock.
// A production adapter MUST verify the complete receipt-record sequence,
// inclusion proofs, and the quorum-cosigned current tree head before return.
type VerifiedWitnessLog interface {
	VerifiedReceiptChain(context.Context, string) ([]Receipt, error)
}

type TransitionVerifier interface {
	VerifyTransition(context.Context, Receipt, Receipt) error
}

type Recovery struct {
	Receipt Receipt
	Checkpoint Checkpoint
	CheckpointSHA256 string
	Complete bool
}

func digest(b []byte) string {
	h := sha256.Sum256(b)
	return hex.EncodeToString(h[:])
}

func validHash(s string) bool {
	if len(s) != 64 { return false }
	b, err := hex.DecodeString(s)
	return err == nil && hex.EncodeToString(b) == s
}

func canonicalCheckpoint(c Checkpoint) ([]byte, error) {
	return json.Marshal(c)
}

func matchManifest(matches []Match) string {
	b, _ := json.Marshal(matches)
	return digest(b)
}

func validateCheckpoint(c Checkpoint) error {
	if c.Profile != checkpointProfile || c.Scope == "" || c.Generation == 0 ||
		!validHash(c.PreviousReceiptSHA256) || !validHash(c.TargetRoot) ||
		!validHash(c.FrontierSHA256) || c.Cursor > c.TargetSize ||
		c.TargetSize >= 1<<63 || c.Matches == nil {
		return fmt.Errorf("%w: checkpoint schema or bounds", ErrHold)
	}
	var previous uint64
	for i, m := range c.Matches {
		if m.Index >= c.Cursor || !validHash(m.Checksum) || (i > 0 && m.Index <= previous) {
			return fmt.Errorf("%w: match list is not canonical", ErrHold)
		}
		previous = m.Index
	}
	if matchManifest(c.Matches) != c.MatchManifestSHA256 {
		return fmt.Errorf("%w: match manifest digest", ErrHold)
	}
	return nil
}

func receiptSigningBytes(r Receipt) ([]byte, error) {
	r.Signature = ""
	return json.Marshal(r)
}

func signReceipt(r Receipt, private ed25519.PrivateKey) (Receipt, error) {
	b, err := receiptSigningBytes(r)
	if err != nil { return Receipt{}, err }
	r.Signature = base64.RawURLEncoding.EncodeToString(ed25519.Sign(private, b))
	return r, nil
}

func receiptBytes(r Receipt) ([]byte, error) {
	return json.Marshal(r)
}

func receiptHash(r Receipt) (string, error) {
	b, err := receiptBytes(r)
	if err != nil { return "", err }
	return digest(b), nil
}

func verifyReceipt(r Receipt, scope, keyID string, public ed25519.PublicKey) error {
	if r.Profile != keeperProfile || r.Scope != scope || r.KeyID != keyID ||
		r.Generation == 0 || !validHash(r.PreviousReceiptSHA256) ||
		!validHash(r.CheckpointSHA256) || !validHash(r.TargetRoot) ||
		!validHash(r.MatchManifestSHA256) || r.CheckpointBytes == 0 {
		return fmt.Errorf("%w: receipt schema or scope", ErrHold)
	}
	sig, err := base64.RawURLEncoding.DecodeString(r.Signature)
	if err != nil || len(sig) != ed25519.SignatureSize {
		return fmt.Errorf("%w: receipt signature encoding", ErrHold)
	}
	b, err := receiptSigningBytes(r)
	if err != nil || !ed25519.Verify(public, b, sig) {
		return fmt.Errorf("%w: keeper signature", ErrHold)
	}
	return nil
}

func samePrefix(old, next []Match) bool {
	if len(next) < len(old) { return false }
	for i := range old {
		if old[i] != next[i] { return false }
	}
	return true
}

func strictCheckpoint(raw []byte) (Checkpoint, error) {
	var c Checkpoint
	if len(raw) == 0 || len(raw) > 1<<20 {
		return c, fmt.Errorf("%w: checkpoint size", ErrHold)
	}
	d := json.NewDecoder(bytes.NewReader(raw))
	d.DisallowUnknownFields()
	if err := d.Decode(&c); err != nil { return c, fmt.Errorf("%w: checkpoint JSON: %v", ErrHold, err) }
	var extra any
	if err := d.Decode(&extra); err != io.EOF { return c, fmt.Errorf("%w: trailing checkpoint data", ErrHold) }
	canonical, err := canonicalCheckpoint(c)
	if err != nil || !bytes.Equal(raw, canonical) {
		return c, fmt.Errorf("%w: noncanonical checkpoint bytes", ErrHold)
	}
	return c, nil
}

// Recover trusts neither the publisher's copy nor its local digest. It requires
// agreement between the independently administered custodian and witnessed
// receipt chain, then validates every immutable checkpoint generation.
func Recover(ctx context.Context, scope, keyID string, public ed25519.PublicKey,
	custodian Custodian, witness VerifiedWitnessLog, transitions TransitionVerifier,
	prior *Floor) (Recovery, error) {
	var out Recovery
	if scope == "" || len(public) != ed25519.PublicKeySize || custodian == nil || witness == nil {
		return out, fmt.Errorf("%w: missing independent source", ErrHold)
	}
	chain, err := witness.VerifiedReceiptChain(ctx, scope)
	if err != nil || len(chain) == 0 {
		return out, fmt.Errorf("%w: witness unavailable or empty: %v", ErrHold, err)
	}
	previousHash := genesisReceipt
	var previousReceipt Receipt
	var previousCheckpoint Checkpoint
	for i, r := range chain {
		if err := verifyReceipt(r, scope, keyID, public); err != nil { return out, err }
		if r.Generation != uint64(i+1) || r.PreviousReceiptSHA256 != previousHash {
			return out, fmt.Errorf("%w: receipt chain fork, gap or rollback", ErrHold)
		}
		raw, err := custodian.Checkpoint(ctx, r.CheckpointSHA256)
		if err != nil { return out, fmt.Errorf("%w: immutable checkpoint missing: %v", ErrHold, err) }
		if uint64(len(raw)) != r.CheckpointBytes || digest(raw) != r.CheckpointSHA256 {
			return out, fmt.Errorf("%w: checkpoint object digest", ErrHold)
		}
		cp, err := strictCheckpoint(raw)
		if err != nil { return out, err }
		if err := validateCheckpoint(cp); err != nil { return out, err }
		if cp.Scope != r.Scope || cp.Generation != r.Generation ||
			cp.PreviousReceiptSHA256 != r.PreviousReceiptSHA256 ||
			cp.Cursor != r.Cursor || cp.TargetSize != r.TargetSize ||
			cp.TargetRoot != r.TargetRoot || cp.MatchManifestSHA256 != r.MatchManifestSHA256 {
			return out, fmt.Errorf("%w: receipt/checkpoint field mismatch", ErrHold)
		}
		if i == 0 {
			if r.PreviousReceiptSHA256 != genesisReceipt { return out, fmt.Errorf("%w: invalid genesis", ErrHold) }
		} else {
			if cp.Cursor < previousCheckpoint.Cursor || !samePrefix(previousCheckpoint.Matches, cp.Matches) {
				return out, fmt.Errorf("%w: cursor rollback or previously discovered match removed", ErrHold)
			}
			if cp.TargetSize < previousCheckpoint.TargetSize {
				return out, fmt.Errorf("%w: sampled target rollback", ErrHold)
			}
			if cp.TargetSize == previousCheckpoint.TargetSize {
				if cp.TargetRoot != previousCheckpoint.TargetRoot || r.TransitionProofSHA256 != "" {
					return out, fmt.Errorf("%w: same-size root conflict or unexpected transition proof", ErrHold)
				}
			} else {
				if r.TransitionProofSHA256 == "" || transitions == nil {
					return out, fmt.Errorf("%w: target growth lacks independently checked consistency proof", ErrHold)
				}
				if err := transitions.VerifyTransition(ctx, previousReceipt, r); err != nil {
					return out, fmt.Errorf("%w: target consistency proof: %v", ErrHold, err)
				}
			}
		}
		previousHash, err = receiptHash(r)
		if err != nil { return out, err }
		previousReceipt, previousCheckpoint = r, cp
	}
	latest, err := custodian.Latest(ctx, scope)
	if err != nil { return out, fmt.Errorf("%w: custodian latest unavailable: %v", ErrHold, err) }
	latestHash, err := receiptHash(latest)
	if err != nil { return out, err }
	if latestHash != previousHash {
		return out, fmt.Errorf("%w: custodian head and witnessed head disagree", ErrHold)
	}
	if err := verifyReceipt(latest, scope, keyID, public); err != nil { return out, err }
	if prior != nil {
		if latest.Generation < prior.Generation ||
			(latest.Generation == prior.Generation && latestHash != prior.ReceiptSHA256) {
			return out, fmt.Errorf("%w: below caller's retained floor", ErrHold)
		}
	}
	out = Recovery{Receipt: previousReceipt, Checkpoint: previousCheckpoint,
		CheckpointSHA256: previousHashForCheckpoint(previousReceipt), Complete: previousCheckpoint.Cursor == previousCheckpoint.TargetSize}
	return out, nil
}

func previousHashForCheckpoint(r Receipt) string { return r.CheckpointSHA256 }
