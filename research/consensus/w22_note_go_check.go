// W22 separate-language reference for a strict subset of C2SP signed-note Ed25519.
// Standalone stdlib, no Ario imports, no signer, no network, no external effects.
// Same research author as Python verifier; NOT an independent human review.
package main

import (
  "bytes"
  "crypto/ed25519"
  "crypto/sha256"
  "encoding/base64"
  "encoding/hex"
  "flag"
  "fmt"
  "os"
  "regexp"
  "strconv"
  "strings"
)

func decodeStrict(src string) ([]byte,error) {
   out,err:=base64.StdEncoding.Strict().DecodeString(src)
   if err!=nil{return nil,err}
   if base64.StdEncoding.EncodeToString(out)!=src{return nil,fmt.Errorf("noncanonical base64")}
   return out,nil
}
func check(pubKeyText string, signedNote []byte, origin string, expectedSize int, expectedRoot string) error {
   kp:=strings.Split(pubKeyText,"+")
   if len(kp)!=3 || kp[0]!=origin || !regexp.MustCompile(`^[0-9a-f]{8}$`).MatchString(kp[1]) {return fmt.Errorf("bad vkey format")}
   keymat,err:=decodeStrict(kp[2]);if err!=nil || len(keymat)!=33 || keymat[0]!=0x01{return fmt.Errorf("bad Ed25519 vkey payload")}
   digest:=sha256.Sum256(append(append([]byte(origin), '\n', 0x01),keymat[1:]...))
   id:=digest[:4]; if hex.EncodeToString(id)!=kp[1] {return fmt.Errorf("vkey key-ID mismatch")}
   sections:=bytes.Split(signedNote,[]byte("\n\n"))
   if len(sections)!=2 || !bytes.HasSuffix(sections[1],[]byte("\n")) {return fmt.Errorf("note delimiters")}
   head:=strings.Split(string(sections[0]),"\n")
   if len(head)!=3 || head[0]!=origin || !regexp.MustCompile(`^(0|[1-9][0-9]*)$`).MatchString(head[1]) {return fmt.Errorf("head grammar")}
   size,err:=strconv.Atoi(head[1]);if err!=nil || size<1 || size>64 || size!=expectedSize {return fmt.Errorf("head size mismatch")}
   root,err:=decodeStrict(head[2]);if err!=nil || len(root)!=32 || hex.EncodeToString(root)!=expectedRoot {return fmt.Errorf("root mismatch")}
   suffix:=string(sections[1])
   prefix:="— "+origin+" "
   if !strings.HasPrefix(suffix,prefix) || !strings.HasSuffix(suffix,"\n") {return fmt.Errorf("signature note line")}
   signed:=strings.TrimSuffix(strings.TrimPrefix(suffix,prefix),"\n")
   if strings.Contains(signed,"\n") {return fmt.Errorf("multiple signature lines unsupported")}
   signature,err:=decodeStrict(signed)
   if err!=nil || len(signature)!=68 || !bytes.Equal(signature[:4],id) {return fmt.Errorf("signature encoding/keyid")}
   text:=append(append([]byte{},sections[0]...), '\n')
   if !ed25519.Verify(keymat[1:],text,signature[4:]) {return fmt.Errorf("Ed25519 signature INVALID")}
   return nil
}
func main() {
   pub:=flag.String("vkey-file","","exact pinned public verifier key file")
   note:=flag.String("note-file","","signed note file")
   origin:=flag.String("origin","","exact expected note origin")
   size:=flag.Int("size",-1,"expected tree size")
   root:=flag.String("root","","expected root hash hex")
   flag.Parse()
   if *pub=="" || *note=="" || *origin=="" || *size<1 || !regexp.MustCompile(`^[0-9a-f]{64}$`).MatchString(*root) {fmt.Fprintln(os.Stderr,"W22_GO_HOLD: required exact trust inputs");os.Exit(2)}
   public,err:=os.ReadFile(*pub);if err!=nil{fmt.Fprintln(os.Stderr,"W22_GO_HOLD: missing pinned key");os.Exit(2)}
   signed,err:=os.ReadFile(*note);if err!=nil{fmt.Fprintln(os.Stderr,"W22_GO_HOLD: missing signed note");os.Exit(2)}
   err=check(strings.TrimSpace(string(public)),signed,*origin,*size,*root)
   if err!=nil{fmt.Fprintln(os.Stderr,"W22_GO_DENY:",err);os.Exit(1)}
   fmt.Println("W22_GO_NOTE_ED25519_VERIFIED / HISTORICAL_ONLY / AUTHORITY=NONE / EXTERNAL_WITNESS=NOT_ESTABLISHED")
}
