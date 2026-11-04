package inventory

import "testing"

func TestReserve(t *testing.T) {
	s := NewStore(map[string]int{"A": 3})
	if err := s.Reserve("A", 2); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got := s.Available("A"); got != 1 {
		t.Fatalf("available = %d, want 1", got)
	}
	if err := s.Reserve("A", 2); err != ErrInsufficientStock {
		t.Fatalf("err = %v, want ErrInsufficientStock", err)
	}
}
