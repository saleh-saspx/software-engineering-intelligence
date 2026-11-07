package shipping

// Address is a postal address.
type Address struct {
	Name     string `json:"name"`
	Street   string `json:"street"`
	City     string `json:"city"`
	Postcode string `json:"postcode"`
	Country  string `json:"country"` // ISO 3166-1 alpha-2
}

// Shipment is what the checkout asks a quote for.
type Shipment struct {
	From        Address `json:"from"`
	To          Address `json:"to"`
	WeightGrams int     `json:"weight_grams"`
}

// Money is an amount in minor units.
type Money struct {
	Cents    int64  `json:"cents"`
	Currency string `json:"currency"`
}

// Quote is one carrier's offer.
type Quote struct {
	Carrier       string `json:"carrier"`
	Service       string `json:"service"`
	Price         Money  `json:"price"`
	EstimatedDays int    `json:"estimated_days"`
}
