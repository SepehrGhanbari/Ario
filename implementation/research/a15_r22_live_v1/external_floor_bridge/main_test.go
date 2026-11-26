package main

import (
 "archive/zip"
 "io"
 "path/filepath"
 "testing"
 "sigsum.org/sigsum-go/pkg/crypto"
)

func fixtureHead(t *testing.T) []byte {
 t.Helper()
 p:=filepath.Join("..","..","..","tests","fixtures","a15_r22_run_45823494521","A15-FIRST-ONLY.zip")
 z,e:=zip.OpenReader(p);if e!=nil{t.Fatal(e)};defer z.Close()
 for _,f:=range z.File {if f.Name=="event-id.txt.proof"{r,e:=f.Open();if e!=nil{t.Fatal(e)};defer r.Close();b,e:=io.ReadAll(r);if e!=nil{t.Fatal(e)};return b}}
 t.Fatal("missing proof");return nil
}
func TestRealExternalPolicy(t *testing.T){
 raw:=fixtureHead(t)
 h,e:=archiveHead(raw);if e!=nil{t.Fatal(e)}
 if _,e=authenticate(&h);e!=nil{t.Fatal(e)}
 remora,_:=crypto.PublicKeyFromHex(witnessKeys["remora"])
 stage,_:=crypto.PublicKeyFromHex(witnessKeys["stagemole"])
 rk,sk:=crypto.HashBytes(remora[:]),crypto.HashBytes(stage[:])
 t.Run("remove second external signature",func(t *testing.T){h,e:=archiveHead(raw);if e!=nil{t.Fatal(e)};delete(h.Cosignatures,sk);if _,e=authenticate(&h);e==nil{t.Fatal("accepted one external signature")}})
 t.Run("remove Remora",func(t *testing.T){h,e:=archiveHead(raw);if e!=nil{t.Fatal(e)};delete(h.Cosignatures,rk);if _,e=authenticate(&h);e==nil{t.Fatal("accepted absent Remora")}})
 t.Run("forged root",func(t *testing.T){h,e:=archiveHead(raw);if e!=nil{t.Fatal(e)};h.RootHash[0]^=1;if _,e=authenticate(&h);e==nil{t.Fatal("accepted wrong signed root")}})
 t.Run("unsigned JSON",func(t *testing.T){if _,e:=archiveHead([]byte("{\"signature_valid\":true}"));e==nil{t.Fatal("accepted unsigned JSON")}})
}
