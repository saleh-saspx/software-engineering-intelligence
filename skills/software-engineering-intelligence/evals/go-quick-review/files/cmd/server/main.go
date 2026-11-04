package main

import (
	"log"
	"net/http"
	"os"

	"github.com/acme/inventory/inventory"
)

func main() {
	store := inventory.NewStore(map[string]int{"WIDGET-1": 100, "GADGET-7": 20})
	h := &inventory.Handler{Store: store, SupplierURL: os.Getenv("SUPPLIER_URL")}

	mux := http.NewServeMux()
	mux.HandleFunc("/reserve", h.ReserveHandler)

	log.Println("listening on :8080")
	log.Fatal(http.ListenAndServe(":8080", mux))
}
