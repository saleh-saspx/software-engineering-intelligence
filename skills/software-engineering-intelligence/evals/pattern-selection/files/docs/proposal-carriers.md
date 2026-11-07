# Proposal: a carrier framework (Sam)

DHL is coming and more carriers will follow, so let's build this properly once.

1. **Abstract Factory.** A `CarrierFactory` interface with `NewRateQuoter()`, `NewLabelPrinter()`
   and `NewTracker()`; `UPSFactory` and `DHLFactory` implement it so each carrier's family of
   objects stays consistent.
2. **Registry singleton.** A package-level `carriers.Registry` that each carrier package fills in
   its `init()` (`carriers.Register("dhl", DHLFactory{})`); the quote service calls
   `carriers.Registry.Get(code)`.
3. **Builder.** A `ShipmentBuilder` with fluent setters (`From`, `To`, `Weight`, `Build`) so
   shipments are always valid.
4. **Plugins.** Load future carriers as Go plugins (`plugin.Open("carriers/fedex.so")`) so we can
   add carriers without redeploying.
5. **Strategy for packing slips.** One `AddressFormatter` implementation per destination country
   instead of the switch in `FormatPackingSlipAddress`.
