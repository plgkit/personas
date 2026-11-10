package main

import "testing"

func TestDemo(t *testing.T) {
	var buf stringsBuilder
	if err := run(&buf); err != nil {
		t.Fatal(err)
	}
	want := "Avery    blocked      Want help with the step you stopped on?\n" +
		"Blake    champion     Bring in the person you invited.\n"
	if buf.String() != want {
		t.Fatalf("%q", buf.String())
	}
}

type stringsBuilder struct{ text string }

func (b *stringsBuilder) Write(p []byte) (int, error) {
	b.text += string(p)
	return len(p), nil
}

func (b *stringsBuilder) String() string { return b.text }
