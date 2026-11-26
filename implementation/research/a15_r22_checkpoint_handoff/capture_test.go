package main

import (
 "strings"
 "testing"
 "sigsum.org/sigsum-go/pkg/types"
)

func TestParseHashStrict(t *testing.T) {
 if _,err:=parseHash(strings.Repeat("a",64)); err!=nil {t.Fatal(err)}
 if _,err:=parseHash("abc"); err==nil {t.Fatal("short hash accepted")}
 if _,err:=parseHash(strings.Repeat("z",64)); err==nil {t.Fatal("non-hex hash accepted")}
}
func TestFloorRejectsStale(t *testing.T) {
 root:=mustHash(floorBRoot)
 if err:=checkFloor(types.TreeHead{Size:floorB-1,RootHash:root},floorPin{Size:floorB,Root:floorBRoot}); err==nil {t.Fatal("stale head accepted")}
}
func TestFloorRejectsSameSizeConflict(t *testing.T) {
 if err:=checkFloor(types.TreeHead{Size:floorB,RootHash:mustHash(floorARoot)},floorPin{Size:floorB,Root:floorBRoot}); err==nil {t.Fatal("same-size conflict accepted")}
}
func TestFloorAcceptsLargerHead(t *testing.T) {
 if err:=checkFloor(types.TreeHead{Size:floorB+1,RootHash:mustHash(floorARoot)},floorPin{Size:floorB,Root:floorBRoot}); err!=nil {t.Fatal(err)}
}
func TestHistoricalLeafPinsAreFixed(t *testing.T) {
 if len(expectedChecksums)!=3 {t.Fatal("wrong fixture count")}
 if expectedChecksums[0]==expectedChecksums[1] || expectedChecksums[1]==expectedChecksums[2] {t.Fatal("fixture pins invalid")}
}
