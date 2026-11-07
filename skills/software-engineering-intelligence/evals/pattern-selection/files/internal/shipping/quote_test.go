package shipping

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"example.com/shipquote/internal/ups"
)

func TestQuoteMapsUPSResponse(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_ = json.NewEncoder(w).Encode(map[string]any{
			"service_name": "UPS Standard", "total_cents": 1290, "currency": "EUR", "transit_days": 2,
		})
	}))
	defer srv.Close()

	svc := NewService(ups.NewClient("test-key", srv.URL))
	q, err := svc.Quote(context.Background(), Shipment{
		From: Address{Postcode: "10115", Country: "DE"}, To: Address{Postcode: "75001", Country: "FR"}, WeightGrams: 1200,
	})
	if err != nil {
		t.Fatal(err)
	}
	if q.Carrier != "UPS" || q.Price.Cents != 1290 || q.EstimatedDays != 2 {
		t.Fatalf("unexpected quote %+v", q)
	}
}

func TestQuoteRejectsZeroWeight(t *testing.T) {
	svc := NewService(ups.NewClient("test-key", "http://unused"))
	if _, err := svc.Quote(context.Background(), Shipment{}); err == nil {
		t.Fatal("expected an error for zero weight")
	}
}

func TestPackingSlipGermany(t *testing.T) {
	got := FormatPackingSlipAddress(Address{Name: "A", Street: "S 1", City: "Berlin", Postcode: "10115", Country: "DE"})
	want := "A\nS 1\n10115 Berlin\nGERMANY"
	if got != want {
		t.Fatalf("got %q want %q", got, want)
	}
}
