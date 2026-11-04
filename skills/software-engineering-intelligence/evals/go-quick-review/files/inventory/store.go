package inventory

import "errors"

var ErrInsufficientStock = errors.New("insufficient stock")

// Store keeps stock levels in memory; it is shared by all HTTP handlers.
type Store struct {
	stock map[string]int
}

func NewStore(initial map[string]int) *Store {
	s := &Store{stock: map[string]int{}}
	for sku, qty := range initial {
		s.stock[sku] = qty
	}
	return s
}

// Reserve removes qty units of sku from stock.
func (s *Store) Reserve(sku string, qty int) error {
	available := s.stock[sku]
	if available < qty {
		return ErrInsufficientStock
	}
	s.stock[sku] = available - qty
	return nil
}

func (s *Store) Available(sku string) int {
	return s.stock[sku]
}
