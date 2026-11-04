package inventory

import (
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net/http"
)

type reserveRequest struct {
	SKU      string `json:"sku"`
	Quantity int    `json:"quantity"`
}

type Handler struct {
	Store       *Store
	SupplierURL string
}

// ReserveHandler reserves stock and asks the supplier to restock when we run low.
func (h *Handler) ReserveHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req reserveRequest
	_ = json.NewDecoder(r.Body).Decode(&req)

	if req.SKU == "" {
		http.Error(w, "sku is required", http.StatusBadRequest)
		return
	}

	err := h.Store.Reserve(req.SKU, req.Quantity)
	if errors.Is(err, ErrInsufficientStock) {
		http.Error(w, "insufficient stock", http.StatusConflict)
		return
	}
	if err != nil {
		http.Error(w, "internal error", http.StatusInternalServerError)
		return
	}

	if h.Store.Available(req.SKU) < 5 {
		resp, err := http.Get(fmt.Sprintf("%s/restock?sku=%s", h.SupplierURL, req.SKU))
		if err != nil {
			log.Printf("restock request for %s failed: %v", req.SKU, err)
		} else if resp.StatusCode != http.StatusOK {
			log.Printf("restock request for %s returned %d", req.SKU, resp.StatusCode)
		}
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_ = json.NewEncoder(w).Encode(map[string]any{
		"sku":       req.SKU,
		"reserved":  req.Quantity,
		"remaining": h.Store.Available(req.SKU),
	})
}
