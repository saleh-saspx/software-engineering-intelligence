package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"

	"example.com/shipquote/internal/shipping"
	"example.com/shipquote/internal/ups"
)

func main() {
	upsClient := ups.NewClient(os.Getenv("UPS_API_KEY"), "https://onlinetools.ups.com")
	svc := shipping.NewService(upsClient)

	http.HandleFunc("POST /quote", func(w http.ResponseWriter, r *http.Request) {
		var sh shipping.Shipment
		if err := json.NewDecoder(r.Body).Decode(&sh); err != nil {
			http.Error(w, "invalid shipment", http.StatusBadRequest)
			return
		}
		q, err := svc.Quote(r.Context(), sh)
		if err != nil {
			log.Printf("quote failed: %v", err)
			http.Error(w, "no quote available", http.StatusBadGateway)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(q)
	})
	log.Fatal(http.ListenAndServe(":8080", nil))
}
