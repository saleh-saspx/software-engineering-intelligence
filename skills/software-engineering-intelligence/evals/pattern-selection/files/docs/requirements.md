# DHL rates — requirements (product, for Q3)

1. For shipments to EU countries, show a DHL Express quote next to the UPS quote and let the
   customer choose. Outside the EU we keep UPS only.
2. Labels keep coming from LabelHub, our label SaaS, for every carrier. No carrier-specific label
   code on our side.
3. Tracking keeps coming from the TrackAll aggregator webhook for every carrier. No
   carrier-specific tracking code on our side.
4. Quote endpoint: p95 under 800 ms. Each carrier API call times out after 2 s. If one carrier
   fails or times out, still return the other carrier's quote.
5. Roadmap: FedEx is being evaluated for 2027. No other carriers are planned. Carriers are always
   integrated by our own team — there is no requirement for third parties to add carriers.
6. We deploy several times a day; adding a carrier is an ordinary code change and release.
