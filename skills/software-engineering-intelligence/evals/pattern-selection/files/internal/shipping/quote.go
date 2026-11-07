package shipping

import (
	"context"
	"errors"
	"fmt"
	"time"

	"example.com/shipquote/internal/ups"
)

// Service quotes shipments.
type Service struct {
	ups *ups.Client
}

// NewService creates a quoting service backed by UPS.
func NewService(c *ups.Client) *Service {
	return &Service{ups: c}
}

// Quote returns the UPS quote for a shipment.
func (s *Service) Quote(ctx context.Context, sh Shipment) (Quote, error) {
	if sh.WeightGrams <= 0 {
		return Quote{}, errors.New("weight must be positive")
	}
	ctx, cancel := context.WithTimeout(ctx, 2*time.Second)
	defer cancel()
	r, err := s.ups.Rate(ctx, ups.RateRequest{
		FromPostcode: sh.From.Postcode,
		FromCountry:  sh.From.Country,
		ToPostcode:   sh.To.Postcode,
		ToCountry:    sh.To.Country,
		WeightGrams:  sh.WeightGrams,
	})
	if err != nil {
		return Quote{}, fmt.Errorf("ups rate: %w", err)
	}
	return Quote{
		Carrier:       "UPS",
		Service:       r.ServiceName,
		Price:         Money{Cents: r.TotalCents, Currency: r.Currency},
		EstimatedDays: r.TransitDays,
	}, nil
}
