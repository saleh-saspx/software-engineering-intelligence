package ups

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
)

// Client calls the UPS rating API.
type Client struct {
	apiKey  string
	baseURL string
	http    *http.Client
}

// NewClient creates a UPS client.
func NewClient(apiKey, baseURL string) *Client {
	return &Client{apiKey: apiKey, baseURL: baseURL, http: &http.Client{}}
}

// RateRequest is the UPS rating request.
type RateRequest struct {
	FromPostcode string `json:"from_postcode"`
	FromCountry  string `json:"from_country"`
	ToPostcode   string `json:"to_postcode"`
	ToCountry    string `json:"to_country"`
	WeightGrams  int    `json:"weight_grams"`
}

// RateResponse is the UPS rating response.
type RateResponse struct {
	ServiceName string `json:"service_name"`
	TotalCents  int64  `json:"total_cents"`
	Currency    string `json:"currency"`
	TransitDays int    `json:"transit_days"`
}

// Rate asks UPS for a rate.
func (c *Client) Rate(ctx context.Context, req RateRequest) (RateResponse, error) {
	body, err := json.Marshal(req)
	if err != nil {
		return RateResponse{}, err
	}
	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, c.baseURL+"/api/rating/v1/shop", bytes.NewReader(body))
	if err != nil {
		return RateResponse{}, err
	}
	httpReq.Header.Set("Authorization", "Bearer "+c.apiKey)
	httpReq.Header.Set("Content-Type", "application/json")
	resp, err := c.http.Do(httpReq)
	if err != nil {
		return RateResponse{}, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return RateResponse{}, fmt.Errorf("ups: status %d", resp.StatusCode)
	}
	var out RateResponse
	if err := json.NewDecoder(resp.Body).Decode(&out); err != nil {
		return RateResponse{}, fmt.Errorf("ups: decode: %w", err)
	}
	return out, nil
}
