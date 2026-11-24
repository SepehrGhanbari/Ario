package replay

import (
 "bytes"
 "crypto/sha256"
 "fmt"
 "net/http"
 "net/http/httptest"
 "os"
 "strings"
 "testing"

 "sigsum.org/sigsum-go/pkg/types"
)

func fixture(t *testing.T, name, want string) []byte {
 t.Helper()
 b,e:=os.ReadFile(os.Getenv(name))
 if e!=nil { t.Fatal(e) }
 if fmt.Sprintf("%x",sha256.Sum256(b))!=want { t.Fatal("fixture pin mismatch") }
 return b
}
func serve(t *testing.T,b []byte,status int,fn func(string,*http.Client)){
 t.Helper()
 calls:=0
 s:=httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter,r *http.Request){
  calls++
  if r.Method!="GET" || !strings.HasSuffix(r.URL.Path,"/get-tree-head") { t.Errorf("unexpected request %s %s",r.Method,r.URL.Path); http.Error(w,"wrong path",404);return }
  w.WriteHeader(status); _,_=w.Write(b)
 }))
 defer s.Close()
 fn(s.URL,s.Client())
 if calls!=1 { t.Fatalf("request count %d",calls) }
}
func TestArchivedResponseReplay(t *testing.T){
 old:=fixture(t,"R22_15_OLD_HEAD","4b03a31a01537968b0636ab18d21d982266cda2b9ce8d82b6e663fd79e8cbb4b")
 newer:=fixture(t,"R22_15_NEW_HEAD","c0c0f5b49ff20a77b36a206d52fc784ef4aa603d7543d4e43a5b345e4c7b3f6b")
 var a,b types.TreeHead
 serve(t,old,200,func(u string,h *http.Client){var s string;a,s=readHead(u,h);if s!="AUTHENTIC_HEAD"||a.Size!=281586 {t.Fatal(s,a.Size)}})
 serve(t,newer,200,func(u string,h *http.Client){var s string;b,s=readHead(u,h);if s!="AUTHENTIC_HEAD"||b.Size!=281587 {t.Fatal(s,b.Size)}})
 t.Log("Both exact archived signed heads authenticated over HTTP")
 mutateRoot:=bytes.Replace(old,[]byte("85ce1600"),[]byte("05ce1600"),1)
 mutateTime:=bytes.ReplaceAll(old,[]byte("1795542819"),[]byte("1795542829"))
 noWitness:=[]byte{}
 for _,line:=range bytes.SplitAfter(old,[]byte("\n")) { if !bytes.HasPrefix(line,[]byte("cosignature=")) {noWitness=append(noWitness,line...)} }
 cases:=[]struct{name string; body []byte; status int; floor *types.TreeHead; want string}{
 {"old_vs_old_floor",old,200,&a,"MATCH_FLOOR_FRESHNESS_UNKNOWN"},
 {"old_vs_new_floor",old,200,&b,"HOLD_HEAD_ROLLBACK"},
 {"new_vs_new_floor",newer,200,&b,"MATCH_FLOOR_FRESHNESS_UNKNOWN"},
 {"new_vs_old_floor",newer,200,&a,"HOLD_ADVANCE_REQUIRES_CONSISTENCY"},
 {"old_without_floor",old,200,nil,"HOLD_FRESHNESS_UNKNOWN"},
 {"new_without_floor",newer,200,nil,"HOLD_FRESHNESS_UNKNOWN"},
 {"joint_floor_rollback_RED",old,200,&a,"MATCH_FLOOR_FRESHNESS_UNKNOWN"},
 {"tampered_root",mutateRoot,200,&b,"HOLD_UNAUTHENTICATED_HEAD"},
 {"tampered_witness_timestamp",mutateTime,200,&b,"HOLD_UNAUTHENTICATED_HEAD"},
 {"missing_quorum",noWitness,200,&b,"HOLD_UNAUTHENTICATED_HEAD"},
 {"malformed_response",[]byte("not a head\n"),200,&b,"HOLD_RESPONSE_UNAVAILABLE_OR_INVALID"},
 {"http_unavailable",nil,503,&b,"HOLD_RESPONSE_UNAVAILABLE_OR_INVALID"},
 }
 for _,c:=range cases {t.Run(c.name,func(t *testing.T){
  serve(t,c.body,c.status,func(u string,h *http.Client){got:=inspect(u,h,c.floor);if got!=c.want {t.Fatalf("got %s want %s",got,c.want)};t.Log(got)})
 })}
 t.Run("same_size_conflict_model_only",func(t *testing.T){conflict:=b;conflict.RootHash[0]^=1;if compare(conflict,&b)!="HOLD_SAME_SIZE_CONFLICT" {t.Fatal("conflict accepted")};t.Log("HOLD_SAME_SIZE_CONFLICT; hypothetical authenticated input, no forged signatures")})
}
